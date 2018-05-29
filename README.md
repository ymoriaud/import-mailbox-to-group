
Import .mbox files to G Suite (formerly Google Apps for Work)

> Freely inspired by import-mailbox-to-group developped by Liron Newman
> https://github.com/google/import-mailbox-to-gmail
> Adapted by Yann Moriaud

This script allows G Suite admins to import mbox files in bulk for groups.

**DISCLAIMER**: This is not an official Google product.


You only authorize it once using a service account, and then it can import mail
into the mailboxes of all groups in your domain.

### A. Creating and authorizing a service account for Gmail API

1. Go to the [Developers Console](https://console.developers.google.com/project)
   and log in as a domain super administrator.

2. Create a new project.

 * If you have not used the API console before, select **Create a project** from
   the **Select a project** dropdown list.
 * If this is not your first project, use the **Create Project** button.

3. Enter "Groups Migration" (or any name you prefer) as the project name and press the
   **Create** button. If this is your first project you must agree to the Terms of
   Service at this point.

4. Click the **Enable and manage APIs** link in the **Use Google APIs** box. 

5. Enable the APIs: 
    1. Select the **Admin SDK** link and press the **Enable API** button.
    1. Select the **Groups Settings API** link and press the **Enable API** button.
    1. Select the **Groups Migration API** link and press the **Enable API** button.

6. Click the 3-line icon (**≡**) in the top left corner of the console.

7. Click **IAM & Admin** and select **Service accounts**.

8. Click **Create service account**.

9. Enter a name (for example, "import-mailbox") in the **Name** field.

10. Check the **Furnish a new private key** box and ensure the key type is set
    to JSON.

11. Check the **Enable G Suite Domain-wide Delegation** box and enter a name
    in the **Product name for the consent screen** field.

12. Click **Create**. You will see a confirmation message advising that the
    Service account JSON file has been downloaded to your computer. Make a note
    of the location and name of this file. **This JSON file contains a private
    key that potentially allows access to all users in your domain. Protect it
    like you'd protect your admin password. Don't share it with anyone.**

13. Click **Close**.

14. Click the **View Client ID** link in the **Options** column.

15. Copy the **Client ID** value. You will need this later.

16. Go to [the **Manage API client access** page of the Admin console for your
    G Suite domain]
    (https://admin.google.com/AdminHome?chromeless=1#OGX:ManageOauthClients).

17. Under **Client Name**, enter the Client ID collected in step 15.

18. Under **One or More API Scopes**, enter the following:
    ```
    https://www.googleapis.com/auth/apps.groups.migration,
    https://www.googleapis.com/auth/apps.groups.settings
    ```
19. Click **Authorize**.

You can now use the JSON file to authorize programs to access the Groups API
"migration" and "settings" scopes of all groups in your G Suite domain.

### B. Importing mbox files using import-mailbox-to-group.py

**Important**: If you're planning to import mail from Apple Mail.app, see the notes below.

1. Download the script - [import-mailbox-to-group.py]().

2. [Download](https://www.python.org/downloads/) and install Python 2.7 (not
   Python 3.x) for your operating system if needed.

3. Open a **Command Prompt** (CMD) window (on Windows) / **Terminal** window
   (on Linux).

4. Install the Google API Client Libraries for Python and their dependencies by
   running, all in one line:

   Mac/Linux:
   ```
   sudo pip install --upgrade google-api-python-client PyOpenSSL
   ```

   Windows:
   ```
   C:\Python27\Scripts\pip install --upgrade google-api-python-client PyOpenSSL
   ```

   **Note**: On Windows, you may need to do this on a Command Prompt window that
   was run as Administrator.

5. Create a folder for the mbox files, for example `C:\mbox`.

6. Under that folder, create a folder for each of the groups into which you
   intend to import the mbox files. The folder names should be the group' full
   email addresses.

7. Into each of the folders, copy the mbox files for that group. Make sure the
   file name format is &lt;LabelName&gt;.mbox. For know the labels are not used when you import them, but the goal is to tags mail when they are imported.

  Your final folder and file structure should look like this (for example):
  ```C:\mbox
  C:\mbox\group1@domain.com
  C:\mbox\group1@domain.com\Imported messages.mbox
  C:\mbox\group1@domain.com\Other imported messages.mbox
  C:\mbox\group2@domain.com
  C:\mbox\group2@domain.com\Imported messages.mbox
  C:\mbox\group2@domain.com\Other imported messages.mbox
  ```

  IMPORTANT: It's essential to test the migration before migrating into the real
  groups' mailboxes. First, migrate the mbox files into a test group, to make sure
  the messages are imported correctly.

8. To start the migration, run the following command (one line):

   Mac/Linux:
   ```
   python import-mailbox-to-group.py --json "cred.json" --dir "mailbox-to-import\" --group_owner admin@domain.com --log "import-mailbox-to-group.log"
   ```

   Windows:
   ```
   C:\Python27\python import-mailbox-to-group.py --json "cred.json" --dir "mailbox-to-import\" --group_owner admin@domain.com --log "import-mailbox-to-group.log"
   ```

  * Replace `import-mailbox-to-group.py` with the full path of import-mailbox-to-group.py -
    usually `~/Downloads/import-mailbox-to-group.py` on Mac/Linux or
    `%USERPROFILE%\Downloads\import-mailbox-to-group.py` on Windows.
  * Replace `Credentials.json` with the path to the JSON file from step 12
    above.
  * Replace `C:\mbox` with the path to the folder you created in step 5.
  * Replace `admin@domain.com` by the user account owner of the group. Apply to _all_ groups and _all_ mbox file.

The mbox files will now be imported, one by one, into the groups' mailboxes. You
can monitor the migration by looking at the output, and inspect errors by
viewing the `import-mailbox-to-group.log` file.

### Options and notes

* Use the `--from_message` parameter to start the upload from a particular message.
  This allows you to resume an upload if the process previously stopped. (Affects
  _all_ groups and _all_ mbox files)

  e.g. `./import-mailbox-to-group.py --from_message 74336`
* If any of the folders have a ".mbox" extension, it will be imported.
* The import mail from Apple Mail.app, is commented. Please check the code before use it.