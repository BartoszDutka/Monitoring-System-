-- Script to remove technician role from the monitoring system database
-- This script will:
-- 1. Update users with technician role to user role
-- 2. Remove role permissions for technician role
-- 3. Remove technician role from roles table

-- Start transaction
START TRANSACTION;

-- Check if technician role exists and show affected users
SELECT 'Users with technician role before update:' as message;
SELECT user_id, username, role FROM users WHERE role = 'technician';

-- Update users with technician role to user role
UPDATE users 
SET role = 'user' 
WHERE role = 'technician';

-- Show updated users
SELECT 'Users updated to user role:' as message;
SELECT user_id, username, role FROM users WHERE role = 'user';

-- Get technician role_id for cleanup
SET @technician_role_id = (SELECT role_id FROM roles WHERE role_key = 'technician');

-- Remove role permissions for technician role
DELETE FROM role_permissions 
WHERE role_id = @technician_role_id;

-- Show remaining role permissions
SELECT 'Remaining role permissions after technician cleanup:' as message;
SELECT rp.*, r.role_key, p.permission_key 
FROM role_permissions rp
JOIN roles r ON rp.role_id = r.role_id
JOIN permissions p ON rp.permission_id = p.permission_id
ORDER BY r.role_key, p.permission_key;

-- Remove technician role from roles table
DELETE FROM roles WHERE role_key = 'technician';

-- Show remaining roles
SELECT 'Remaining roles after technician removal:' as message;
SELECT * FROM roles ORDER BY role_key;

-- Commit the transaction
COMMIT;

-- Show final summary
SELECT 'Final role distribution:' as message;
SELECT role, COUNT(*) as user_count 
FROM users 
GROUP BY role 
ORDER BY role;
