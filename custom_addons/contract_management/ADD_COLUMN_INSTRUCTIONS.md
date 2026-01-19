# Instructions to Add is_contract Column

## The column needs to be added manually via SQL

Odoo doesn't automatically create columns for inherited models. You need to add it manually.

## Step 1: Connect to PostgreSQL

Find your database name from your Odoo configuration or check the error logs.

## Step 2: Run this SQL command

```sql
ALTER TABLE res_partner ADD COLUMN is_contract BOOLEAN DEFAULT FALSE;
```

## Step 3: Verify the column was added

```sql
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name='res_partner' AND column_name='is_contract';
```

You should see one row with:
- column_name: is_contract
- data_type: boolean
- column_default: false

## Step 4: After adding the column

1. Restart Odoo
2. Uncomment the lines in:
   - models/__init__.py (uncomment `from . import res_partner`)
   - models/contract.py (uncomment the domain line)
   - models/contract_amendment_wizard.py (uncomment the domain line)
   - __manifest__.py (uncomment `'views/res_partner_views.xml'`)

## How to run SQL:

### Option 1: Via psql command line
```bash
psql -U odoo -d your_database_name -c "ALTER TABLE res_partner ADD COLUMN is_contract BOOLEAN DEFAULT FALSE;"
```

### Option 2: Connect to psql interactively
```bash
psql -U odoo -d your_database_name
```
Then paste:
```sql
ALTER TABLE res_partner ADD COLUMN is_contract BOOLEAN DEFAULT FALSE;
```

### Option 3: Use pgAdmin or any PostgreSQL GUI tool
Connect to your database and run the SQL command in the query editor.

