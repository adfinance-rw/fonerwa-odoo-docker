# Diagnostic Guide: Why Emails Are Not Sending

## Quick Diagnostic Steps

### Step 1: Check Your Contract

Run this in Odoo console (Settings > Technical > Python Code):

```python
# Find your contract
contract = env['contract.management'].search([
    ('expiry_date', '=', '2025-09-11')  # Your expiry date
], limit=1)

if contract:
    print("=" * 60)
    print("CONTRACT DIAGNOSTIC")
    print("=" * 60)
    print(f"Contract Number: {contract.contract_number}")
    print(f"Contract Name: {contract.name}")
    print(f"Status: {contract.state}")
    print(f"Expiry Date: {contract.expiry_date}")
    print(f"Days to Expiry: {contract.days_to_expiry}")
    print(f"Notice Period: {contract.notice_period_days}")
    print(f"Send Recurring Reminders: {contract.send_recurring_reminders}")
    print(f"Expiration Notification Sent: {contract.expiration_notification_sent}")
    print(f"Last Notification Date: {contract.last_notification_date}")
    print(f"\nContract Manager: {contract.contract_manager_id.name if contract.contract_manager_id else 'None'}")
    print(f"Contract Manager Email: {contract.contract_manager_id.email if contract.contract_manager_id else 'None'}")
    
    # Check if it should notify
    from odoo import fields
    today = fields.Date.today()
    notice_period = contract.notice_period_days or 7
    days_to_expiry = (contract.expiry_date - today).days
    
    print(f"\n" + "=" * 60)
    print("SHOULD SEND EMAIL?")
    print("=" * 60)
    print(f"Contract is Active: {contract.state == 'active'}")
    print(f"Days to Expiry: {days_to_expiry}")
    print(f"Notice Period: {notice_period}")
    print(f"Within Notice Period: {0 <= days_to_expiry <= notice_period}")
    print(f"Recurring Reminders Enabled: {contract.send_recurring_reminders}")
    print(f"Has Contract Manager: {contract.contract_manager_id is not False}")
    print(f"Manager Has Email: {contract.contract_manager_id.email if contract.contract_manager_id else False}")
    
    should_notify = (
        contract.state == 'active' and
        0 <= days_to_expiry <= notice_period and
        contract.send_recurring_reminders and
        contract.contract_manager_id and
        contract.contract_manager_id.email
    )
    
    print(f"\nShould Send Email: {'YES ✓' if should_notify else 'NO ✗'}")
    
    if not should_notify:
        print("\nREASONS WHY NOT:")
        if contract.state != 'active':
            print("  ✗ Contract is not Active")
        if not (0 <= days_to_expiry <= notice_period):
            print(f"  ✗ Outside notice period (days: {days_to_expiry}, period: {notice_period})")
        if not contract.send_recurring_reminders:
            print("  ✗ Recurring reminders are disabled")
        if not contract.contract_manager_id:
            print("  ✗ No contract manager assigned")
        if not contract.contract_manager_id.email:
            print("  ✗ Contract manager has no email address")
else:
    print("Contract not found!")
```

### Step 2: Check Email Server Configuration

```python
# Check email server
mail_servers = env['ir.mail_server'].search([])
print(f"\nEmail Servers Found: {len(mail_servers)}")
for server in mail_servers:
    print(f"  - {server.name}: Active={server.active}, SMTP={server.smtp_host}")
```

### Step 3: Check Email Queue

```python
# Check recent mail messages
recent_mails = env['mail.mail'].search([
    ('model', '=', 'contract.management')
], order='create_date desc', limit=10)

print(f"\nRecent Mail Messages: {len(recent_mails)}")
for mail in recent_mails:
    print(f"  - {mail.subject}: State={mail.state}, To={mail.email_to}")
```

### Step 4: Manually Test Email Sending

```python
# Test sending email directly
contract = env['contract.management'].search([
    ('expiry_date', '=', '2025-09-11')
], limit=1)

if contract:
    print("\nTesting email sending...")
    try:
        result = contract.send_expiration_notification()
        print(f"Result: {result}")
        print(f"Notification Sent: {contract.expiration_notification_sent}")
        print(f"Last Notification: {contract.last_notification_date}")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
```

### Step 5: Check Logs

After running the cron job manually, check the Odoo logs for detailed information:

Look for lines like:
- `Contract Renewal Reminder: Starting check`
- `Contract Renewal Reminder: Found X active contracts`
- `Contract Renewal Reminder: Checking contract...`
- `Contract Renewal Reminder: Sending notification...`
- `Contract Renewal Reminder: Successfully sent...`

## Common Issues and Solutions

### Issue 1: No Contracts Found
**Symptom**: Logs show "Found 0 active contracts"
**Solution**: 
- Check contract status is "Active"
- Check expiry date is in the future
- Check "Send Recurring Reminders" is enabled

### Issue 2: Contract Manager Has No Email
**Symptom**: Logs show "Contract manager has no email address"
**Solution**: 
- Go to Users/Employees
- Find the contract manager
- Add email address

### Issue 3: Email Server Not Configured
**Symptom**: Emails created but not sent (state = 'outgoing')
**Solution**: 
- Go to Settings > Technical > Outgoing Mail Servers
- Configure SMTP server
- Test connection

### Issue 4: Contract Outside Notice Period
**Symptom**: Logs show "Outside notice period"
**Solution**: 
- Check days to expiry
- Check notice period days
- Adjust notice period if needed

### Issue 5: Email Template Not Found
**Symptom**: Logs show "Email template not found"
**Solution**: 
- Upgrade the module
- Check email_templates.xml is in manifest
- Verify template exists in database

## Next Steps

1. **Run the diagnostic script above** to identify the issue
2. **Check the Odoo logs** after running the cron job manually
3. **Fix the identified issue** based on the diagnostic results
4. **Test again** by running the cron job manually

