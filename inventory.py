from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
from modules.database import get_db_cursor
import pdfplumber
import re
import os
import json
import tempfile
from werkzeug.utils import secure_filename

inventory = Blueprint('inventory', __name__)

@inventory.route('/inventory')
def view_inventory():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    # Get all departments with their equipment count
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT 
                d.name,
                d.description_en,
                COUNT(DISTINCT e.id) as equipment_count
            FROM departments d
            LEFT JOIN equipment e ON e.assigned_to_department = d.name
            GROUP BY d.name, d.description_en
            ORDER BY d.name
        ''')
        departments = cursor.fetchall()
    
    # Get current user's department
    current_department = None
    if 'username' in session:
        username = session.get('username')
        with get_db_cursor() as cursor:
            cursor.execute('SELECT Department FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            if user:
                current_department = user['Department']
    
    # Get language preference from session or default to English
    lang = session.get('language', 'en')
    
    return render_template('inventory.html', 
                         departments=departments, 
                         current_department=current_department,
                         lang=lang)

@inventory.route('/api/department_equipment/<department>')
def get_department_equipment(department):
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
        
    with get_db_cursor() as cursor:
        # Get department info
        cursor.execute('''
            SELECT name, description_en as description, location
            FROM departments
            WHERE name = %s
        ''', (department,))
        dept_info = cursor.fetchone()
        
        # Get equipment for department
        cursor.execute('''
            SELECT 
                e.id,
                e.name,
                e.type,
                e.serial_number,
                e.status,
                e.quantity,
                e.assigned_date,
                e.notes
            FROM equipment e
            WHERE e.assigned_to_department = %s
            ORDER BY e.type, e.name
        ''', (department,))
        equipment = cursor.fetchall()
        
    return jsonify({
        'department': dept_info,
        'equipment': [dict(item) for item in equipment]  # Convert row objects to dictionaries
    })

# Update the assign equipment function
@inventory.route('/api/equipment/assign', methods=['POST'])
def assign_equipment():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    data = request.json
    try:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE equipment 
                SET assigned_to_department = %s, 
                    assigned_date = %s,
                    status = 'assigned',
                    quantity = %s
                WHERE id = %s
            ''', (
                data['department'],
                datetime.now().strftime('%Y-%m-%d'),
                data.get('quantity', 1),
                data['equipment_id']
            ))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Update the add equipment function
@inventory.route('/api/equipment/add', methods=['POST'])
def add_equipment():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    data = request.form
    try:
        with get_db_cursor() as cursor:
            # First check if department exists
            if data.get('assignTo'):
                cursor.execute('''
                    SELECT name FROM departments 
                    WHERE name = %s
                ''', (data.get('assignTo'),))
                if not cursor.fetchone():
                    return jsonify({'error': 'Invalid department selected'}), 400

            cursor.execute('''
                INSERT INTO equipment (
                    name, type, serial_number, status, 
                    acquisition_date, value, description,
                    manufacturer, model, notes, quantity,
                    assigned_to_department
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    data.get('itemName'),
                    data.get('itemCategory'),
                    data.get('itemSerial'),
                    data.get('itemStatus', 'available'),
                    data.get('acquisitionDate'),
                    data.get('itemValue'),
                    data.get('itemDescription'),
                    data.get('itemManufacturer'),
                    data.get('itemModel'),
                    data.get('itemNotes'),
                    data.get('itemQuantity', 1),
                    data.get('assignTo')  # This is the department name
                ))
            
        return jsonify({'success': True, 'item_id': cursor.lastrowid})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@inventory.route('/api/person_equipment/<int:person_id>')
def get_person_equipment(person_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT id, name, type, serial_number, status, 
                assigned_date, notes, quantity
            FROM equipment
            WHERE assigned_to = %s
            ORDER BY type, name
        ''', (person_id,))
        equipment = cursor.fetchall()
        
        cursor.execute('''
            SELECT user_id as id, display_name as name, Department as department, email 
            FROM users 
            WHERE user_id = %s
        ''', (person_id,))
        person = cursor.fetchone()
    
    return jsonify({
        'person': person,
        'equipment': equipment
    })

@inventory.route('/api/equipment/unassign', methods=['POST'])
def unassign_equipment():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    data = request.json
    try:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE equipment 
                SET assigned_to = NULL, 
                    assigned_date = NULL,
                    status = 'available'
                WHERE id = %s
            ''', (data['equipment_id'],))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@inventory.route('/api/invoice/process', methods=['POST'])
def process_invoice():
    """Process PDF invoice and extract data"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Authentication required'}), 401
    
    if 'invoice_pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    invoice_file = request.files['invoice_pdf']
    
    if invoice_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not invoice_file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    try:
        print(f"Processing invoice: {invoice_file.filename}")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            invoice_file.save(temp_file.name)
            print(f"Saved to temp file: {temp_file.name}")
            
            # Extract data with more detailed logging
            invoice_data = extract_invoice_data(temp_file.name)
        
        # Delete the temporary file
        os.unlink(temp_file.name)
        
        if invoice_data.get('error'):
            print(f"Extraction error: {invoice_data['error']}")
            return jsonify({'error': invoice_data['error']}), 400
        
        print(f"Extraction complete: {len(invoice_data.get('products', []))} products found")
        return jsonify(invoice_data)
    
    except Exception as e:
        print(f"Exception during invoice processing: {str(e)}")
        return jsonify({'error': 'Failed to process invoice: ' + str(e)}), 500

def extract_invoice_data(pdf_path):
    """Extract data from invoice PDF using multiple strategies"""
    try:
        invoice_data = {
            'invoice_number': None,
            'invoice_date': None,
            'vendor': None,
            'total_amount': None,
            'products': []
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            # Combine text content from all pages
            text_content = ""
            for page in pdf.pages:
                text_content += page.extract_text() or ""
            
            print(f"Extracted text length: {len(text_content)}")
            
            # Try different extraction methods and combine results
            
            # 1. Extract basic invoice info from text
            basic_info = extract_invoice_info(text_content)
            invoice_data.update(basic_info)
            
            # 2. Extract tables from all pages with multiple methods
            all_tables = []
            for page in pdf.pages:
                tables = extract_all_tables(page)
                all_tables.extend(tables)
                
                # Also try table extraction with different settings
                try:
                    alt_tables = page.extract_tables({
                        'vertical_strategy': 'text',
                        'horizontal_strategy': 'text',
                        'min_words_horizontal': 2
                    })
                    if alt_tables:
                        all_tables.extend(alt_tables)
                except Exception:
                    pass
            
            # 3. Analyze tables for invoice info
            table_info = analyze_tables_for_info(all_tables)
            for key, value in table_info.items():
                # Only update if value is not None and current value is None
                if value is not None and invoice_data.get(key) is not None:
                    invoice_data[key] = value
            
            # 4. Extract products from tables
            table_products = extract_products_from_tables(all_tables)
            invoice_data['products'].extend(table_products)
            
            # 5. Extract products from text if table extraction failed
            if not invoice_data['products']:
                text_products = extract_products_from_text(text_content)
                invoice_data['products'].extend(text_products)
            
            # 6. Try additional extraction methods
            if not invoice_data['products']:
                # Try additional pattern-based extraction
                pattern_products = extract_products_by_pattern(text_content)
                invoice_data['products'].extend(pattern_products)
                
                # Try layout-based extraction
                for page in pdf.pages:
                    layout_products = extract_products_from_layout(page)
                    invoice_data['products'].extend(layout_products)
            
            # 7. Advanced OCR fallback could be added here
            
            # Clean and validate products
            invoice_data['products'] = [p for p in invoice_data['products'] 
                                     if validate_product(p)]
            
            # Deduplicate products
            unique_products = {}
            for product in invoice_data['products']:
                name = product['name']
                if name not in unique_products or product.get('confidence', 0) > unique_products[name].get('confidence', 0):
                    unique_products[name] = product
            
            invoice_data['products'] = list(unique_products.values())
            
            # Sort products by confidence
            invoice_data['products'].sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Debug output
            print(f"Found {len(invoice_data['products'])} products")
            
        return invoice_data
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return {'error': f'Error processing PDF: {str(e)}'}

def extract_tables_from_pdf(pdf):
    """Extract tables from all pages of the PDF"""
    all_tables = []
    for page in pdf.pages:
        tables = extract_all_tables(page)
        if tables:
            tables = [t for t in tables if is_valid_table(t)]
            all_tables.extend(tables)
    return all_tables

def extract_products_from_tables(tables):
    """Extract products from a list of tables"""
    products = []
    for table in tables:
        table_products = process_table_data(table)
        products.extend(table_products)
    return products

def extract_products_from_layout_all_pages(pages):
    """Extract products from layout analysis of all pages"""
    products = []
    for page in pages:
        layout_products = extract_products_from_layout(page)
        products.extend(layout_products)
    return products

def extract_all_tables(page):
    """Extract tables using multiple methods with different settings"""
    tables = []
    
    try:
        # Method 1: Standard table extraction
        standard_tables = page.extract_tables()
        if standard_tables:
            tables.extend([t for t in standard_tables if t and len(t) > 1])
        
        # Method 2: Try with different settings for text-based tables
        text_tables = page.extract_tables({
            'vertical_strategy': 'text',
            'horizontal_strategy': 'text',
            'intersection_y_tolerance': 10
        })
        if text_tables:
            tables.extend([t for t in text_tables if t and len(t) > 1])
        
        # Method 3: Try with even more relaxed settings
        relaxed_tables = page.extract_tables({
            'vertical_strategy': 'lines_strict',
            'horizontal_strategy': 'lines',
            'intersection_y_tolerance': 15
        })
        if relaxed_tables:
            tables.extend([t for t in relaxed_tables if t and len(t) > 1])
        
        # Method 4: Try to construct tables from layout analysis
        # Extract words with their positions
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if words:
            # Group words by approximate y-position (lines)
            lines = {}
            for word in words:
                y = round(word['top'])
                if y not in lines:
                    lines[y] = []
                lines[y].append(word)
            
            # Convert to table format
            if lines:
                table = []
                for y in sorted(lines.keys()):
                    # Sort words in line by x position
                    line_words = sorted(lines[y], key=lambda w: w['x0'])
                    row = [w['text'] for w in line_words]
                    if row:
                        table.append(row)
                
                if len(table) > 1:  # Need at least 2 rows
                    tables.append(table)
        
        # Return unique tables
        unique_tables = []
        seen = set()
        for table in tables:
            table_str = str(table)
            if table_str not in seen:
                seen.add(table_str)
                unique_tables.append(table)
                
        return unique_tables
    
    except Exception as e:
        print(f"Error extracting tables: {str(e)}")
        return []

def is_valid_table(table):
    """Check if table contains valid data"""
    if not table or len(table) < 2:  # Need at least header and one data row
        return False
    
    # Check if table has enough columns and non-empty cells
    return any(row and len(row) >= 3 and any(cell and str(cell).strip() for cell in row) 
              for row in table)

def validate_product(product):
    """Validate product data and calculate confidence score"""
    if not product or not product.get('name'):
        return False
        
    name = str(product['name']).strip().lower()
    
    # Skip invalid entries
    invalid_keywords = ['razem', 'suma', 'total', 'vat', 'podatek', 'dostawa', 
                        'wartość', 'netto', 'brutto', 'amount', 'metoda']
    if any(keyword in name for keyword in invalid_keywords):
        return False
        
    if len(name) < 3:
        return False
    
    # Calculate confidence score
    confidence = product.get('confidence', 0)
    if confidence == 0:
        confidence = 0.3  # Base confidence
        
        # Name quality
        if len(name) > 5:
            confidence += 0.2
        if any(char.isdigit() for char in name):  # Model numbers often contain digits
            confidence += 0.1
        
        # Price validation
        quantity = float(product.get('quantity', 0))
        unit_price = float(product.get('unit_price', 0))
        total_price = float(product.get('total_price', 0))
        
        if quantity > 0 and unit_price > 0:
            confidence += 0.2
            # Check if total price matches quantity * unit price
            expected_total = quantity * unit_price
            if total_price > 0 and abs(expected_total - total_price) / max(expected_total, total_price) < 0.05:
                confidence += 0.2
        
        product['confidence'] = confidence
    
    return confidence > 0.4  # Lower threshold to catch more potential products

def merge_product_lists(list1, list2):
    """Merge two product lists, removing duplicates and invalid entries"""
    merged = {}
    
    for product in list1 + list2:
        if not validate_product(product):
            continue
            
        name = str(product['name']).strip()
        if not name:
            continue
            
        # If product already exists, keep the one with higher confidence
        if name in merged:
            if product.get('confidence', 0) > merged[name].get('confidence', 0):
                merged[name] = product
        else:
            merged[name] = product
    
    return list(merged.values())

def extract_invoice_info(text):
    """Extract basic invoice information using multiple patterns"""
    info = {}
    
    # Invoice number patterns - enhanced with more variations
    invoice_patterns = [
        r'(?:Faktura|FV|Invoice|Rachunek)(?:\s+VAT)?(?:\s+nr\.?|\s+number:?|\s+#)?[\s:]*([\w\d/-]+)',
        r'(?:Nr\s+dokumentu|Document\s+no\.?|Nr\.?)[:\s]*([\w\d/-]+)',
        r'(?:Numer|Number|Nr\.?)[:\s]*([\w\d/-]+)',
        r'(?:Invoice|Faktura)[:\s]*(?:#|nr\.?)[:\s]*([\w\d/-]+)',
        r'(?:F\.?V\.?)[:\s]*([\w\d/-]+)',
        r'^(?:\s*)([\d]{1,4}[\/][\d]{1,4}[\/][\d]{1,4})(?:\s*)'  # Simple pattern like 123/45/2023
    ]
    
    # Date patterns - enhanced with more formats
    date_patterns = [
        r'(?:Data|Date)(?:\s+wystawienia)?[\s:]*((?:\d{2}|\d{4})[-./](?:\d{1,2})[-./](?:\d{1,2}|\d{4}))',
        r'(?:Data\s+sprzedaży|Sale\s+date|Data\s+trans\.?)[:\s]*((?:\d{2}|\d{4})[-./](?:\d{1,2})[-./](?:\d{1,2}|\d{4}))',
        r'(?:Wystawiono|Issued)[:\s]*((?:\d{2}|\d{4})[-./](?:\d{1,2})[-./](?:\d{1,2}|\d{4}))',
        r'(?:Data|Date)[:\s]*(?:\d{1,2})[-./\s](?:\d{1,2})[-./\s](?:\d{2}|\d{4})',
        r'(?:Data|Date)[:\s]*(?:\d{1,2})\s+(?:stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)\s+(?:\d{4})'
    ]
    
    # Vendor patterns - enhanced to catch more cases
    vendor_patterns = [
        r'(?:Sprzedawca|Vendor|Seller|Wystawca)[:\s]+(.*?)(?=(?:NIP|Nabywca|Buyer|$))',
        r'(?:Dane\s+sprzedawcy)[:\s]+(.*?)(?=(?:NIP|Nabywca|Buyer|$))',
        r'(?:Sprzedający|Seller)[:\s]+(.*?)(?=(?:NIP|Nabywca|Buyer|$))',
        r'(?:SPRZEDAWCA)[:\s]+(.*?)(?=(?:NABYWCA|$))'
    ]
    
    # Try each pattern until we find a match
    for pattern in invoice_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            info['invoice_number'] = clean_text(match.group(1))
            break
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            info['invoice_date'] = normalize_date(match.group(1))
            break
    
    for pattern in vendor_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            vendor = clean_text(match.group(1))
            # Take only first two non-empty lines
            vendor_lines = [line.strip() for line in vendor.split('\n') if line.strip()][:2]
            info['vendor'] = ' '.join(vendor_lines)
            break
    
    # Extract total amount - enhanced patterns
    total_patterns = [
        r'(?:Razem|Total|Suma|SUMA)(?:\s+do\s+zapłaty)?[\s:]*([\d\s,.]+)(?:\s*(?:PLN|EUR|USD|zł))?',
        r'(?:Wartość\s+całkowita|Total\s+value|Wartość\s+sprzedaży)[:\s]*([\d\s,.]+)',
        r'(?:Do\s+zapłaty|Amount\s+due|ZAPŁACONO|WARTOŚĆ)[:\s]*([\d\s,.]+)',
        r'(?:Łącznie|Grand\s+total)[:\s]*([\d\s,.]+)',
        r'(?:RAZEM|DO\s+ZAPŁATY)[:\s]*([\d\s,.]+)',
    ]
    
    for pattern in total_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                info['total_amount'] = parse_number(match.group(1))
                break
            except (ValueError, TypeError):
                continue
    
    return info

def process_table_data(table):
    """Process data from extracted table to identify products"""
    if not table or len(table) < 2:
        return []
        
    products = []
    col_indices = identify_columns(table[0]) or guess_columns_from_data(table)
    
    if not col_indices:
        return []
    
    data_rows = find_data_rows(table)
    
    for row in data_rows:
        try:
            name = get_column_value(row, col_indices, 'name', 0)
            if not name or not is_valid_product_name(name):
                continue
            
            # Extract and validate numeric values
            quantity = get_column_value(row, col_indices, 'quantity', default=1, numeric=True)
            unit_price = get_column_value(row, col_indices, 'unit_price', 'price', numeric=True)
            total_price = get_column_value(row, col_indices, 'total_price', 'total', 'sum', numeric=True)
            
            # Skip invalid entries
            if quantity <= 0 or unit_price <= 0:
                continue
                
            # Calculate missing values
            if not total_price:
                total_price = quantity * unit_price
            elif not unit_price and quantity > 0:
                unit_price = total_price / quantity
            
            products.append({
                'name': clean_text(name),
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': total_price
            })
        except:
            continue
    
    return products

def get_column_value(row, col_indices, *keys, default=None, numeric=False):
    """Get column value from row using multiple possible column keys"""
    value = default
    
    # Try each key in the column indices
    for key in keys:
        if key in col_indices and col_indices[key] < len(row):
            cell_value = row[col_indices[key]]
            if cell_value is not None and cell_value != '':
                value = cell_value
                break
    
    # Convert to number if needed
    if numeric and value is not None:
        try:
            return parse_number(value)
        except (ValueError, TypeError):
            return default
    
    return clean_text(value) if value is not None else default

def analyze_tables_for_info(tables):
    """Extract invoice information from tables"""
    info = {
        'invoice_number': None,
        'invoice_date': None,
        'vendor': None,
        'total_amount': None
    }
    
    if not tables:
        return info
        
    # Look for patterns in first few rows of each table
    for table in tables:
        if not table:
            continue
            
        for row in table[:5]:  # Check first 5 rows
            row_text = ' '.join(str(cell) for cell in row if cell)
            row_text_lower = row_text.lower()
            
            # Look for invoice number
            if any(keyword in row_text_lower for keyword in ['faktura', 'invoice', 'fv']):
                match = re.search(r'(?:nr|no)\.?\s*([A-Za-z0-9/-]+)', row_text, re.IGNORECASE)
                if match:
                    info['invoice_number'] = clean_text(match.group(1))
            
            # Look for date
            if any(keyword in row_text_lower for keyword in ['data', 'date']):
                date_match = re.search(r'\d{2}[-./]\d{2}[-./]\d{4}|\d{4}[-./]\d{2}[-./]\d{2}', row_text)
                if date_match:
                    info['invoice_date'] = normalize_date(date_match.group(0))
            
            # Look for vendor
            if any(keyword in row_text_lower for keyword in ['sprzedawca', 'vendor', 'seller']):
                next_cell_idx = next((i for i, cell in enumerate(row) if any(k in str(cell).lower() 
                                    for k in ['sprzedawca', 'vendor', 'seller'])), None)
                if next_cell_idx is not None and next_cell_idx + 1 < len(row):
                    info['vendor'] = clean_text(row[next_cell_idx + 1])
            
            # Look for total amount
            if any(keyword in row_text_lower for keyword in ['razem', 'total', 'suma']):
                amounts = re.findall(r'\d+(?:[,.]\d+)?', row_text)
                if amounts:
                    # Take the largest amount as total
                    info['total_amount'] = max(parse_number(amount) for amount in amounts)
    
    return info

def analyze_numeric_patterns(table):
    """Analyze patterns in numeric data to identify column roles"""
    if len(table) < 3:  # Need enough rows for pattern analysis
        return {}
    
    # Skip header row
    data_rows = table[1:]
    num_rows = len(data_rows)
    num_cols = max(len(row) for row in data_rows)
    
    # Create arrays to track numeric properties
    is_numeric = [0] * num_cols  # Count of numeric cells
    avg_values = [0] * num_cols  # Average value in each column
    value_ranges = [(float('inf'), 0)] * num_cols  # Min/max in each column
    
    # Collect statistics on all columns
    for row in data_rows:
        for i in range(min(len(row), num_cols)):
            if not row[i]:
                continue
                
            try:
                val = parse_number(row[i])
                if val > 0:  # Valid positive number
                    is_numeric[i] += 1
                    avg_values[i] += val
                    # Update min/max
                    current_min, current_max = value_ranges[i]
                    value_ranges[i] = (min(current_min, val), max(current_max, val))
            except (ValueError, TypeError):
                pass
    
    # Calculate average values for columns with numeric data
    for i in range(num_cols):
        if is_numeric[i] > 0:
            avg_values[i] /= is_numeric[i]
    
    # Determine column roles based on patterns
    col_indices = {}
    
    # Find text column for product name (first column with mostly non-numeric data)
    for i in range(num_cols):
        if is_numeric[i] <= num_rows * 0.3:  # Less than 30% numeric
            col_indices['name'] = i
            break
    
    # Find numeric columns and classify them
    numeric_cols = [(i, is_numeric[i], avg_values[i], value_ranges[i]) 
                    for i in range(num_cols) 
                    if is_numeric[i] > num_rows * 0.5]  # At least 50% numeric
    
    if numeric_cols:
        # Sort by column index for predictable ordering
        numeric_cols.sort(key=lambda x: x[0])
        
        # Typically: quantity, unit price, total price
        if len(numeric_cols) >= 3:
            # Find small values (likely quantity)
            for idx, count, avg, (min_val, max_val) in numeric_cols:
                if avg < 10 and max_val < 100:  # Typical quantity range
                    col_indices['quantity'] = idx
                    break
            
            # Remove found quantity column if any
            if 'quantity' in col_indices:
                numeric_cols = [c for c in numeric_cols if c[0] != col_indices['quantity']]
            
            # Find remaining columns with larger values (prices)
            if numeric_cols:
                # Sort by average value
                numeric_cols.sort(key=lambda x: x[2])
                
                # Smaller value likely unit price, larger one total price
                if len(numeric_cols) >= 2:
                    col_indices['unit_price'] = numeric_cols[0][0]
                    col_indices['total_price'] = numeric_cols[1][0]
                else:
                    col_indices['unit_price'] = numeric_cols[0][0]
        elif len(numeric_cols) == 2:
            # Likely quantity and unit price
            numeric_cols.sort(key=lambda x: x[2])  # Sort by average value
            col_indices['quantity'] = numeric_cols[0][0]
            col_indices['unit_price'] = numeric_cols[1][0]
        elif len(numeric_cols) == 1:
            # Likely unit price or total
            col_indices['unit_price'] = numeric_cols[0][0]
    
    return col_indices

def find_data_rows(table):
    """Find product data rows by filtering out headers and footers"""
    if not table or len(table) < 3:  # Need at least header + data + footer
        return table[1:] if len(table) > 1 else []
    
    # Identify and skip header rows
    header_row_idx = 0
    for i in range(min(3, len(table))):
        row = table[i]
        header_indicators = ['name', 'product', 'item', 'description', 'quantity', 
                            'price', 'amount', 'total', 'nazwa', 'produkt', 
                            'ilość', 'cena', 'wartość']
        
        # Check if row contains header keywords
        if any(any(keyword in str(cell).lower() for keyword in header_indicators) 
               for cell in row if cell):
            header_row_idx = i
    
    # Identify and skip footer rows
    footer_start_idx = len(table)
    for i in range(len(table)-1, max(header_row_idx, 0), -1):
        row = table[i]
        footer_indicators = ['total', 'sum', 'razem', 'suma', 'vat', 'subtotal',
                            'tax', 'shipping', 'discount', 'grand']
        
        # Check if row contains footer keywords
        if any(any(keyword in str(cell).lower() for keyword in footer_indicators) 
               for cell in row if cell):
            footer_start_idx = i
            break
    
    # Return rows between header and footer
    data_rows = table[header_row_idx+1:footer_start_idx]
    
    # Filter out empty rows and rows that don't look like product entries
    return [row for row in data_rows if row and any(row) and 
            sum(1 for cell in row if cell and str(cell).strip()) >= 2]

def extract_all_tables(page):
    """Extract tables using multiple methods with different settings"""
    tables = []
    
    # Method 1: Standard table extraction
    try:
        standard_tables = page.extract_tables()
        if standard_tables:
            tables.extend(standard_tables)
    except Exception:
        pass
    
    # Method 2: Try with different settings for text-based tables
    try:
        text_tables = page.extract_tables({
            'vertical_strategy': 'text',
            'horizontal_strategy': 'text',
            'intersection_y_tolerance': 10,
            'min_words_horizontal': 3
        })
        if text_tables:
            tables.extend(text_tables)
    except Exception:
        pass
    
    # Method 3: Try with even more relaxed settings
    try:
        relaxed_tables = page.extract_tables({
            'vertical_strategy': 'lines_strict',
            'horizontal_strategy': 'lines',
            'intersection_y_tolerance': 15,
            'intersection_x_tolerance': 15
        })
        if relaxed_tables:
            tables.extend(relaxed_tables)
    except Exception:
        pass
    
    # Method 4: Try to construct tables from layout analysis
    try:
        # Extract words with their positions
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if words:
            # Group words by approximate y-position (lines)
            lines = {}
            for word in words:
                y = round(word['top'])
                if y not in lines:
                    lines[y] = []
                lines[y].append(word)
            
            # Convert to table format
            if lines:
                table = []
                for y in sorted(lines.keys()):
                    # Sort words in line by x position
                    line_words = sorted(lines[y], key=lambda w: w['x0'])
                    row = [w['text'] for w in line_words]
                    if row:
                        table.append(row)
                
                if len(table) > 1:  # Need at least 2 rows
                    tables.append(table)
    except Exception:
        pass
    
    return tables

def extract_products_from_text(text):
    """Extract products from text content using multiple regex patterns"""
    products = []
    
    # Pattern 1: Look for lines with numbers that might indicate products
    pattern1 = r'(?:\d+\.|\*|\-)\s*([A-Za-z0-9\s\-\+\.]{3,}?)(?:\s{2,})(\d+(?:[\s,.]\d+)?)(?:\s{2,})(\d+(?:[\s,.]\d+)?)(?:\s{2,})(\d+(?:[\s,.]\d+)?)'
    
    # Pattern 2: More general pattern with less strict spacing
    pattern2 = r'([A-Za-z0-9\s\-\+\.]{5,}?)(?:\s+)(\d+(?:[\s,.]\d+)?)(?:\s+)(\d+(?:[\s,.]\d+)?)(?:\s+)(\d+(?:[\s,.]\d+)?)'
    
    # Pattern 3: Very relaxed pattern for difficult formats
    pattern3 = r'([A-Za-z0-9\s\-\+\.]{5,})(?:.*?)(\d+(?:[\s,.]\d+)?)(?:.*?)(\d+(?:[\s,.]\d+)?)(?:.*?)(\d+(?:[\s,.]\d+)?)'
    
    # Try all patterns and combine results
    patterns = [pattern1, pattern2, pattern3]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                name = clean_text(match[0])
                if not name or len(name) < 3 or is_header_or_footer(name):
                    continue
                    
                # Try to parse numbers - be flexible with formats
                quantity = parse_number(match[1]) if match[1] else 1
                unit_price = parse_number(match[2]) if len(match) > 2 and match[2] else 0
                total_price = parse_number(match[3]) if len(match) > 3 and match[3] else quantity * unit_price
                
                if quantity > 0 and (unit_price > 0 or total_price > 0):
                    # If we have total but no unit price, calculate it
                    if unit_price == 0 and total_price > 0 and quantity > 0:
                        unit_price = total_price / quantity
                    
                    products.append({
                        'name': name,
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total_price': total_price,
                        'confidence': 0.7  # Set confidence for text extraction
                    })
            except (ValueError, IndexError):
                continue
    
    # Also try line-by-line analysis for difficult formats
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if not line.strip() or len(line.strip()) < 10:
            continue
            
        # Look for lines that have numeric content
        numbers = re.findall(r'\d+(?:[,.]\d+)?', line)
        if len(numbers) >= 2:
            # First part is likely product name, rest could be quantities and prices
            name_part = re.split(r'\d+[,.]\d+|\d+', line)[0].strip()
            
            if name_part and len(name_part) > 5 and not is_header_or_footer(name_part):
                try:
                    # Try to identify quantity and price
                    quantity = 1
                    unit_price = 0
                    total_price = 0
                    
                    # Parse numbers in order found
                    if len(numbers) >= 1:
                        quantity = parse_number(numbers[0])
                    if len(numbers) >= 2:
                        unit_price = parse_number(numbers[1])
                    if len(numbers) >= 3:
                        total_price = parse_number(numbers[2])
                    else:
                        total_price = quantity * unit_price
                    
                    if quantity > 0 and (unit_price > 0 or total_price > 0):
                        products.append({
                            'name': name_part,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total_price': total_price,
                            'confidence': 0.6  # Lower confidence for this method
                        })
                except:
                    continue
    
    return products

def extract_products_from_layout(page):
    """Extract products based on text positioning and layout analysis"""
    products = []
    
    try:
        # Extract words with position info
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if not words:
            return []
        
        # Group words by approximate y-position (lines)
        lines = {}
        for word in words:
            y = round(word['top'])
            if y not in lines:
                lines[y] = []
            lines[y].append(word)
        
        # Find potential product rows based on number patterns
        sorted_y_positions = sorted(lines.keys())
        
        for i, y in enumerate(sorted_y_positions):
            if i < 1:  # Skip potential header row
                continue
            
            line_words = lines[y]
            # Sort words by x position
            line_words.sort(key=lambda w: w['x0'])
            
            # Extract text for this line
            line_text = ' '.join([w['text'] for w in line_words])
            
            # Check if this line contains numbers that might indicate product info
            if not re.search(r'\d', line_text):
                continue
            
            # Look for number patterns that could be quantity and price
            number_pattern = r'\d+(?:[,.]\d+)?'
            numbers = re.findall(number_pattern, line_text)
            
            if len(numbers) >= 2:  # Need at least quantity and price
                # Extract name - typically the text before numbers start
                name_words = []
                for word in line_words:
                    if not re.match(r'^\d+(?:[,.]\d+)?$', word['text']):
                        name_words.append(word['text'])
                    else:
                        # Stop once we hit a standalone number
                        break
                        
                name = ' '.join(name_words)
                
                # Try to parse numbers as quantity and prices
                try:
                    quantity = parse_number(numbers[0])
                    unit_price = parse_number(numbers[1])
                    total_price = parse_number(numbers[2]) if len(numbers) > 2 else quantity * unit_price
                    
                    if is_valid_product_name(name) and quantity > 0 and unit_price > 0:
                        products.append({
                            'name': name,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total_price': total_price
                        })
                except (ValueError, IndexError):
                    pass
        
        return products
    except Exception:
        return []

def extract_products_by_pattern(text):
    """Extract products by looking for repeating patterns in text structure"""
    products = []
    
    # Split text into lines
    lines = text.split('\n')
    
    # Look for consecutive lines that might be products
    product_section = False
    potential_products = []
    
    product_keywords = ['produkt', 'usługa', 'towar', 'artykuł', 'product', 'item', 'service', 'artikel']
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Check if this might be a product section header
        if any(keyword.lower() in line.lower() for keyword in product_keywords) and not product_section:
            product_section = True
            continue
            
        # If we found potential product section and line contains numbers
        if product_section and re.search(r'\d', line):
            # Skip lines that are likely headers or footers
            if is_header_or_footer(line):
                continue
                
            # Skip lines that are too short
            if len(line) < 10:
                continue
                
            # Check if line has multiple numbers (likely product details)
            numbers = re.findall(r'\d+(?:[,.]\d+)?', line)
            if len(numbers) >= 2:
                potential_products.append(line)
    
    # Process potential product lines
    for line in potential_products:
        # Try to split line into segments
        segments = re.split(r'\s{2,}', line)
        
        if len(segments) >= 3:
            # First segment is likely the name
            name = segments[0].strip()
            
            # Look for numbers in the remaining segments
            number_matches = []
            for segment in segments[1:]:
                match = re.search(r'\d+(?:[\s,.]\d+)?', segment)
                if match:
                    number_matches.append(match.group())
            
            if len(number_matches) >= 2 and is_valid_product_name(name):
                try:
                    quantity = parse_number(number_matches[0])
                    unit_price = parse_number(number_matches[1])
                    total_price = parse_number(number_matches[2]) if len(number_matches) > 2 else quantity * unit_price
                    
                    if quantity > 0 and unit_price > 0:
                        products.append({
                            'name': name,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'total_price': total_price
                        })
                except (ValueError, IndexError):
                    pass
    
    return products

def is_header_or_footer(text):
    """Check if text appears to be a header or footer rather than product"""
    text = text.lower()
    keywords = [
        'faktura', 'invoice', 'razem', 'total', 'suma', 'netto', 'brutto',
        'vat', 'page', 'strona', 'data', 'date', 'nr', 'number',
        'sprzedawca', 'seller', 'nabywca', 'buyer', 'klient', 'client',
        'adres', 'address', 'nip', 'tax', 'podpis', 'signature'
    ]
    
    return any(keyword in text for keyword in keywords)

def clean_product_data(products):
    """Clean and validate product data"""
    cleaned = []
    seen_names = set()
    
    for product in products:
        name = clean_text(product['name'])
        if not name or name in seen_names:
            continue
            
        seen_names.add(name)
        cleaned.append({
            'name': name,
            'quantity': round(float(product['quantity']), 2),
            'unit_price': round(float(product['unit_price']), 2),
            'total_price': round(float(product['total_price']), 2)
        })
    
    return cleaned

def normalize_date(date_str):
    """Normalize date string to YYYY-MM-DD format"""
    if not date_str:
        return None
        
    # Remove any non-numeric or separator characters
    date_str = re.sub(r'[^\d/.-]', '', date_str)
    
    # Try different date formats
    for pattern in ['%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y', '%d.%m.%Y']:
        try:
            date_obj = datetime.strptime(date_str, pattern)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return date_str

def has_numeric_content(text):
    """Check if text contains any numeric values"""
    if not text:
        return False
    return bool(re.search(r'\d+(?:[,.]\d+)?', str(text)))

def process_table_with_lines(page):
    """Alternative approach to extract table data using lines and text positioning"""
    products = []
    
    try:
        # Extract horizontal and vertical lines to identify table structure
        horizontal_lines = [line for line in page.lines if abs(line['y0'] - line['y1']) < 1]
        vertical_lines = [line for line in page.lines if abs(line['x0'] - line['x1']) < 1]
        
        if not (horizontal_lines and vertical_lines):
            return []
            
        # Extract text with positioning
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        
        if not words:
            return []
            
        # Group words by line (y-position)
        lines = {}
        for word in words:
            y = int(word['top'])
            if y not in lines:
                lines[y] = []
            lines[y].append(word)
        
        # Sort lines by y-position and convert to table format
        table = []
        sorted_lines = sorted(lines.items())
        
        for _, line_words in sorted_lines:
            # Sort words by x position
            sorted_words = sorted(line_words, key=lambda w: w['x0'])
            row = [w['text'] for w in sorted_words]
            if any(has_numeric_content(cell) for cell in row):
                table.append(row)
        
        return table if len(table) > 1 else None
    except Exception:
        return []

def identify_columns(header_row):
    """Identify column indices based on header text"""
    col_indices = {}
    
    if not header_row:
        return {}
        
    for i, cell in enumerate(header_row):
        if not cell:
            continue
            
        cell_lower = str(cell).lower()
        
        # Check for name/description column
        if any(kw in cell_lower for kw in ['nazwa', 'name', 'towar', 'product', 'item', 'description', 'produkt']):
            col_indices['name'] = i
        
        # Check for quantity column
        if any(kw in cell_lower for kw in ['ilość', 'ilosc', 'quantity', 'qty', 'szt', 'pcs']):
            col_indices['quantity'] = i
            
        # Check for unit price column
        if any(kw in cell_lower for kw in ['cena', 'price', 'unit', 'netto', 'net']):
            col_indices['price'] = i
            
        # Check for total price column
        if any(kw in cell_lower for kw in ['wartość', 'wartosc', 'amount', 'total', 'brutto', 'suma', 'sum']):
            col_indices['total'] = i
    
    return col_indices

def guess_columns_from_data(table):
    """Try to guess column structure from data when headers aren't clear"""
    if len(table) < 2:
        return {}
        
    # Analyze a few data rows to identify columns
    numeric_cols = set()
    text_cols = set()
    
    # Start from index 1 to skip potential header
    for row_idx in range(1, min(5, len(table))):
        for col_idx, cell in enumerate(table[row_idx]):
            if cell is None or cell == '':
                continue
                
            cell_str = str(cell)
            # Check if cell contains a number
            if re.search(r'\d+(?:[,.]\d+)?', cell_str) and not re.search(r'[a-zA-Z]', cell_str):
                numeric_cols.add(col_idx)
            elif len(cell_str) > 3:
                text_cols.add(col_idx)
    
    # Make best guess about column roles
    col_indices = {}
    
    # First text column is likely the product name
    if text_cols:
        col_indices['name'] = min(text_cols)
    
    # For numeric columns, try to determine which is which
    numeric_cols_sorted = sorted(numeric_cols)
    if len(numeric_cols_sorted) >= 3:
        # Common pattern: quantity, unit price, total price
        col_indices['quantity'] = numeric_cols_sorted[0]
        col_indices['price'] = numeric_cols_sorted[1]
        col_indices['total'] = numeric_cols_sorted[2]
    elif len(numeric_cols_sorted) == 2:
        # Probably quantity and price
        col_indices['quantity'] = numeric_cols_sorted[0]
        col_indices['price'] = numeric_cols_sorted[1]
    
    return col_indices

def find_data_rows(table):
    """Identify which rows contain actual data (skip headers and footers)"""
    if len(table) <= 1:
        return []
        
    # First row is typically header, last row might be total
    data_rows = table[1:-1]
    
    # Filter out empty rows or rows that don't look like product entries
    return [row for row in data_rows if row and any(row)]

def clean_text(text):
    """Clean and normalize text values"""
    if text is None:
        return ""
        
    text = str(text).strip()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text

def parse_number(value):
    """Parse numeric values from string, handling different formats"""
    if value is None:
        return 0.0
        
    # Convert to string if not already
    value_str = str(value).strip()
    
    # If empty, return 0
    if not value_str:
        return 0.0
    
    # Remove non-numeric characters except for , and .
    value_str = re.sub(r'[^\d,.-]', '', value_str)
    
    # Handle empty result after filtering
    if not value_str:
        return 0.0
    
    # Handle different number formats
    if ',' in value_str and '.' in value_str:
        # For formats like 1,234.56
        if value_str.find(',') < value_str.find('.'):
            value_str = value_str.replace(',', '')
        # For formats like 1.234,56
        else:
            value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str:
        # Check if comma is decimal separator (e.g., 1234,56) or thousands (e.g., 1,234)
        parts = value_str.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely a decimal separator
            value_str = value_str.replace(',', '.')
        else:
            # Likely a thousands separator
            value_str = value_str.replace(',', '')
    
    # Handle negative values
    is_negative = value_str.startswith('-')
    value_str = value_str.replace('-', '')
    
    try:
        result = float(value_str)
        return -result if is_negative else result
    except ValueError:
        # Return 0 if conversion fails
        return 0.0

def extract_products_from_text(text):
    """Extract products from text content using regex patterns"""
    products = []
    
    # Split text into lines and process each line
    lines = text.split('\n')
    
    for line in lines:
        # Skip empty lines or too short lines
        if not line or len(line.strip()) < 5:
            continue
            
        # Try to match product pattern: name followed by numbers
        # Looking for patterns like: "Product Name    quantity    price    total"
        matches = re.findall(r'''
            ^([^0-9]+?)\s+                          # Product name (non-numeric)
            (\d+(?:[,.]\d+)?)\s+                   # Quantity
            (\d+(?:[,.]\d+)?)\s+                   # Unit price
            (\d+(?:[,.]\d+)?)                      # Total price
        ''', line.strip(), re.VERBOSE)
        
        for match in matches:
            try:
                name = clean_text(match[0])
                
                # Skip if not a valid product name
                if not is_valid_product_name(name):
                    continue
                    
                quantity = parse_number(match[1])
                unit_price = parse_number(match[2])
                total_price = parse_number(match[3])
                
                # Validate numbers
                if quantity <= 0 or unit_price <= 0 or total_price <= 0:
                    continue
                    
                # Validate total price (allow small differences due to rounding)
                expected_total = quantity * unit_price
                if not (0.98 <= total_price/expected_total <= 1.02):
                    continue
                
                products.append({
                    'name': name,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'total_price': total_price
                })
            except (ValueError, IndexError):
                continue
    
    return products

def is_valid_product_name(name):
    """Check if a string seems like a valid product name"""
    if not name or len(name.strip()) < 2:
        return False
        
    name = name.lower()
    
    # Keywords that indicate real IT products
    it_keywords = [
        'komp', 'laptop', 'pc', 'monitor', 'drukarka', 'notebook',
        'windows', 'office', 'microsoft', 'hp', 'dell', 'lenovo',
        'asus', 'acer', 'ram', 'dysk', 'cpu', 'intel', 'amd',
        'router', 'switch', 'access point', 'kamera', 'ups',
        'ssd', 'hdd', 'klawiatura', 'myszka', 'zasilacz',
        'licencja', 'system', 'software', 'procesor'
    ]
    
    # Invalid patterns and keywords that indicate non-products
    invalid_patterns = [
        r'^\d+[.,]\d{2}$',  # Just numbers with decimals
        r'słownie:?',  # Word-form amounts
        r'zł\s*\d+/100',  # Currency fractions
        r'pozostało\s+do\s+zapłaty:?',  # Payment remainders
        r'na\s+podstawie\s+zamówienia',  # Order references
        r'razem:?|suma:?|total:?',  # Totals
        r'wartość\s+\w+:?',  # Value labels
        r'do\s+zapłaty:?',  # Payment due
        r'nr:?|numer:?',  # Numbers/references
        r'\d{2}-\d{3}',  # Postal codes
        r'\d{4}-\d{2}-\d{2}',  # Dates
        r'tel\.?|fax|email',  # Contact info
        r'faktura\s+nr|paragon|rachunek',  # Document types
        r'płatność|termin|dostawa',  # Payment/delivery terms
        r'adres|siedziba|oddział',  # Addresses
        r'pln:?|eur:?|usd:?',  # Currency indicators
        r'vat\s*\d+%',  # VAT rates
        r'\d+\s*dni',  # Day counts
        r'uwagi|notatki',  # Notes
        r'strona\s*\d+',  # Page numbers
        r'klient|nabywca|odbiorca',  # Customer references
        r'zk\s*\d+/\d+/\d+',  # Order numbers
        r'^[a-z\s]+:\s*$',  # Label-only lines
        r'^\s*\d+\s*$',  # Just numbers
        r'^\s*[a-z]+\s*$' # Just a word
    ]
    
    # Check if it matches any invalid patterns
    if any(re.search(pattern, name, re.IGNORECASE) for pattern in invalid_patterns):
        return False
    
    # Check for common IT product patterns
    it_pattern = re.compile(r'''
        (?:
            \w+\s*\d+\s*(?:G\d|GB|TB|MHz|GHz)  # Memory/storage/frequency specs
            |
            [A-Za-z]+\s*\d{3,}                  # Model numbers
            |
            i[3579]-\d{4,}                      # Intel processors
            |
            ryzen\s*\d                          # AMD processors
            |
            r\d{2,}\s*\d{2,}                   # Product codes
        )
    ''', re.VERBOSE | re.IGNORECASE)
    
    # Return True if it contains IT keywords or matches IT product patterns
    return any(keyword in name for keyword in it_keywords) or bool(it_pattern.search(name))
