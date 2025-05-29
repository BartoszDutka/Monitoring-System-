-- Script to remove 'operator' role from the monitoring system database
-- This script will:
-- 1. Update users with 'operator' role to 'user' role
-- 2. Remove role_permissions entries for operator role
-- 3. Remove operator role from roles table

USE monitoring_system;

-- Step 1: Check if operator role exists and show current users with this role
SELECT 'Current users with operator role:' as info;
SELECT user_id, username, email, role, department 
FROM users 
WHERE role = 'operator';

-- Step 2: Update users with 'operator' role to 'user' role
UPDATE users 
SET role = 'user' 
WHERE role = 'operator';

-- Step 3: Get operator role_id for cleanup
SET @operator_role_id = (SELECT role_id FROM roles WHERE role_key = 'operator');

-- Step 4: Remove role_permissions entries for operator role
DELETE FROM role_permissions 
WHERE role_id = @operator_role_id;

-- Step 5: Remove operator role from roles table
DELETE FROM roles 
WHERE role_key = 'operator';

-- Step 6: Verify cleanup
SELECT 'Verification - Users after role update:' as info;
SELECT DISTINCT role, COUNT(*) as count 
FROM users 
GROUP BY role 
ORDER BY role;

SELECT 'Verification - Remaining roles:' as info;
SELECT role_key, description_en, description_pl 
FROM roles 
ORDER BY FIELD(role_key, 'admin', 'manager', 'technician', 'user', 'viewer');

SELECT 'Cleanup completed successfully!' as result;
