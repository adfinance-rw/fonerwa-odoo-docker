# Production Deployment Instructions for Odoo.sh

## Issue
The `is_contract` column needs to be added to the `res_partner` table before the module can use it.

## Step 1: Deploy Current Version (with res_partner disabled)
The current code has `res_partner` temporarily disabled so the app can start.

## Step 2: Add Column via Odoo.sh Database Interface

1. **Go to Odoo.sh Dashboard**
2. **Select your database** (adfinance-rw-testv18-test-26835660)
3. **Click on "Database"** or **"SQL"** option
4. **Run this SQL command:**
   ```sql
   ALTER TABLE res_partner ADD COLUMN IF NOT EXISTS is_contract BOOLEAN DEFAULT FALSE;
   ```

## Step 3: Verify Column Was Added

Run this query to verify:
```sql
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name='res_partner' AND column_name='is_contract';
```

You should see one row returned.

## Step 4: Re-enable res_partner Model

After the column is added, uncomment these lines:

1. **In `models/__init__.py`:**
   ```python
   from . import res_partner  # Uncomment this line
   ```

2. **In `models/contract.py`:**
   ```python
   domain=[('is_contract', '=', True)],  # Uncomment this line
   ```

3. **In `models/contract_amendment_wizard.py`:**
   ```python
   domain=[('is_contract', '=', True)],  # Uncomment this line
   ```

4. **In `__manifest__.py`:**
   ```python
   'views/res_partner_views.xml',  # Uncomment this line
   ```

## Step 5: Deploy Updated Version

1. Commit the changes
2. Push to your Odoo.sh repository
3. The module will upgrade automatically

## Alternative: Use Migration Script

If you prefer, you can bump the version number to `18.0.1.0.2` and the pre-migration script should run automatically when upgrading.

