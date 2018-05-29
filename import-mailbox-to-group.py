# Freely inspired by import-mailbox-to-gmail developped by Liron Newman
# https://github.com/google/import-mailbox-to-gmail

# Adapted by Yann Moriaud

# CLI example
# python import-mailbox-to-group.py --json "cred.json" --dir "mailbox-to-import" --group_owner admin@domain.com --log "logs.txt"

"""
Shows basic usage of the Admin SDK Groups Settings API. Outputs a group's
settings identified by the group's email address.
"""

import argparse
import base64
import io
import json
import logging
import logging.handlers
import mailbox
import os
import sys

from apiclient import discovery
from apiclient.http import set_user_agent
import httplib2
from apiclient.http import MediaIoBaseUpload
from oauth2client.service_account import ServiceAccountCredentials
import oauth2client.tools
import OpenSSL  # Required by Google API library, but not checked by it

APPLICATION_NAME = 'import-mailbox-to-group'
APPLICATION_VERSION = '0.1'

SCOPES = ['https://www.googleapis.com/auth/apps.groups.settings',
  'https://www.googleapis.com/auth/apps.groups.migration']


parser = argparse.ArgumentParser(
    description='Import mbox files to a specified label for many users.',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[oauth2client.tools.argparser],
    epilog=
    """
 * The directory needs to have a subdirectory for each group (with the full
   email address as the name), and in it there needs to be a separate .mbox
   file for each label. File names must end in .mbox.

 * Filename format: <group@domain.com>/<labelname>.mbox.
   Example: support@mycompany.com/Migrated messages.mbox - This is a file named
   "Migrated messages.mbox" in the "support@mycompany.com" subdirectory.
   It will be imported into support@mycompany.com's Group.
""")
parser.add_argument(
    '--json',
    required=True,
    help='Path to the JSON key file from https://console.developers.google.com')
parser.add_argument(
    '--group_owner',
    required=True,
    help='Email address from the owner of the groups')
parser.add_argument(
    '--dir',
    required=True,
    help=
    'Path to the directory that contains group directories with mbox files to '
    'import')
parser.add_argument(
    '--log',
    required=False,
    default='%s-%d.log' % (APPLICATION_NAME, os.getpid()),
    help=
    'Optional: Path to a the log file (default: %s-####.log in the current '
    'directory, where #### is the process ID)' % APPLICATION_NAME)
parser.add_argument(
    '--from_message',
    default=0,
    type=int,
    help=
      'Message number to resume from, affects ALL users and ALL '
      'mbox files (default: 0)')
parser.set_defaults(fix_msgid=True, replace_quoted_printable=True,
                    logging_level='INFO')
args = parser.parse_args()


def get_credentials(username):
  """Gets valid user credentials from a JSON service account key file.

  Args:
    username: The email address of the user to impersonate.
  Returns:
    Credentials, the obtained credential.
  """
  credentials = ServiceAccountCredentials.from_json_keyfile_name(
      args.json,
      scopes=SCOPES).create_delegated(username)

  return credentials

def process_mbox_files(group_name, service):
  """Iterates over the mbox files found in the user's subdir and imports them.

  Args:
    group_name: The email address of the group to import into.
    service: A Gmail API service object.
  Returns:
    A tuple of: Number of labels imported without error,
                Number of labels imported with some errors,
                Number of labels that failed completely,
                Number of messages imported without error,
                Number of messages that failed.
  """
  number_of_labels_imported_without_error = 0
  number_of_labels_imported_with_some_errors = 0
  number_of_labels_failed = 0
  number_of_messages_imported_without_error = 0
  number_of_messages_failed = 0
  base_path = os.path.join(args.dir, group_name)
  for root, dirs, files in os.walk(base_path):
    for dir in dirs:
      try:
        labelname = os.path.join(root[len(base_path) + 1:], dir)
      except Exception:
        logging.error("Labels under '%s' may not nest correctly", dir)
    for file in files:
      filename = root[len(base_path) + 1:]
      if filename:
        filename += '/'
      filename += file
      labelname, ext = os.path.splitext(filename)
      full_filename = os.path.join(root, file)
      if labelname.endswith('.mbox/mbox'):
          logging.error("It's seem to be Apple Mail export. It's not handled by the script")
        # Assume this is an Apple Mail export, so there's an mbox file inside a
        # dir that ends with .mbox.
        # labelname = labelname[:-10]
        # logging.info("File '%s' looks like an Apple Mail export, importing it "
        #              "into label '%s'",
        #              full_filename,
        #              labelname)
      elif ext != '.mbox':
        logging.info("Skipping '%s' because it doesn't have a .mbox extension",
                     full_filename)
        continue
      if os.path.isdir(full_filename):
        # This "shouldn't happen" but it does, sometimes.
        # Assume this is an Apple Mail export, so there's an mbox file inside the dir.
        full_filename += os.path.join(full_filename, 'mbox')
        logging.info("Using '%s' instead of the directory", full_filename)
      logging.info("Starting processing of '%s'", full_filename)
      number_of_successes_in_label = 0
      number_of_failures_in_label = 0
      mbox = mailbox.mbox(full_filename)

      logging.info("Using label name '%s'", labelname)
      total = len(mbox)
      for index, message in enumerate(mbox):
        if index < args.from_message:
          continue
        logging.info("Processing message %d/%d in label '%s'", index, total, labelname)
        try:
          # Use media upload to allow messages more than 5mb.
          # See https://developers.google.com/api-client-library/python/guide/media_upload
          # and http://google-api-python-client.googlecode.com/hg/docs/epy/apiclient.http.MediaIoBaseUpload-class.html.
          if sys.version_info.major == 2:
            message_data = io.BytesIO(message.as_string())
          else:
            message_data = io.StringIO(message.as_string())
          media = MediaIoBaseUpload(message_data, mimetype='message/rfc822')
          service.archive().insert(
              groupId=group_name,
              media_body=media).execute()
          number_of_successes_in_label += 1

        except Exception:
          number_of_failures_in_label += 1
          logging.exception('Failed to import mbox message')
      logging.info("Finished processing '%s'. %d messages imported "
                   "successfully, %d messages failed.",
                   full_filename,
                   number_of_successes_in_label,
                   number_of_failures_in_label)
      if number_of_failures_in_label == 0:
        number_of_labels_imported_without_error += 1
      elif number_of_successes_in_label > 0:
        number_of_labels_imported_with_some_errors += 1
      else:
        number_of_labels_failed += 1
      number_of_messages_imported_without_error += number_of_successes_in_label
      number_of_messages_failed += number_of_failures_in_label
  return (number_of_labels_imported_without_error,     # 0
          number_of_labels_imported_with_some_errors,  # 1
          number_of_labels_failed,                     # 2
          number_of_messages_imported_without_error,   # 3
          number_of_messages_failed)                   # 4

def main():

  # Set the default encoding for logger
  reload(sys)
  sys.setdefaultencoding('utf8')

  # Setup logging
  httplib2.debuglevel = 0

  # Increase log leven of file_cache error on oauth2client >= 4.0.0
  # https://github.com/google/google-api-python-client/issues/299
  logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
  logging.getLogger('googleapiclient').setLevel(logging.ERROR)

  try:
      logging_level = args.logging_level
  except AttributeError:
      logging_level = 'INFO'

  logging.basicConfig(
      level=logging_level,
      format='%(asctime)s %(levelname)s %(message)s',
      datefmt='%H:%M:%S')

  # More detailed logging to file
  file_handler = logging.handlers.RotatingFileHandler(args.log,
                                                      maxBytes=1024 * 1024 * 32,
                                                      backupCount=8)
  file_formatter = logging.Formatter(
      '%(asctime)s '
      '(%(filename)s:%(lineno)d) %(message)s')
  file_formatter.datefmt = '%Y-%m-%dT%H:%M:%S (%z)'
  file_handler.setFormatter(file_formatter)
  logging.getLogger().addHandler(file_handler)

  for group_name in next(os.walk(args.dir))[1]:
      logging.info('Processing group %s', group_name)
      credentials = get_credentials(args.group_owner)
      http = credentials.authorize(set_user_agent(
          httplib2.Http(),
          '%s-%s' % (APPLICATION_NAME, APPLICATION_VERSION)))
      service_settings = discovery.build('groupssettings', 'v1', http=http)

      try:
          results = service_settings.groups().get(groupUniqueId=group_name, alt='json').execute()
          logging.info('Successfully found group %s', group_name)
      except Exception:
          logging.error("Can't get group %s", group_name)
          raise

      try:
          service_migration = discovery.build('groupsmigration', 'v1', http=http)
          result = process_mbox_files(group_name, service_migration)
          logging.info('Done importing user %s. Labels: %d succeeded, %d with some '
                  'errors, %d failed. Messages: %d succeeded, %d failed.',
                  group_name,
                  result[0],
                  result[1],
                  result[2],
                  result[3],
                  result[4])
      except Exception:
          logging.error("Can't process mbox files for group %s", group_name)
          raise
  logging.info('Finished.\n\n')

if __name__ == '__main__':
  main()