import json
import os

for filename in os.listdir("."):
    print(f"Checking {filename}...")
    if filename.endswith('.bak'):
        filename = filename[:-4]
        if not os.path.isfile(filename):
            print("Backup file without cleaned har file. re-cleaning.")
            os.rename(filename + '.bak', filename)
        else:
            print("Not a HAR archive file. Skipping.")
            continue
    if not filename.endswith('.har'):
        print("Not a HAR archive file. Skipping.")
        continue
    with open(filename, 'r', encoding='utf-8') as file:
        obj = json.load(file)
    if type(obj) == dict and not obj.get('cleaned', False):
        print("Classified as unprocessed file. Cleaning...")
        entries = []
        images = []
        for entry in obj['log']['entries']:
            request = entry['request']
            response = entry['response']
            resp_content = response['content']
            # if 'mimeType' in resp_content:
            #     mimetype: str = resp_content['mimeType']
            #     match = False
            #     for ext in Proxy.EXTENSIONS:
            #         if ext[1:] in mimetype:
            #             match = True
            #             break
            #     if not match:
            #         continue
            # else:
            #     continue
            # headers = {}
            # for header in response['headers']:
            #     headers[header['name']] = header['value']
            entries.append({
                'request': {
                    'method': request['method'],
                    'url': request['url']
                },
                'response': {
                    'status': response['status'],
                    'content': response['content'],
                    'cookies': response['cookies'],
                    'headers': response['headers'],
                    'redirectURL': response['redirectURL']
                }
            })
        print("Cleaned data. Making backup of old file. Writing back to disk.")
        os.rename(filename, filename + ".bak")
        with open(filename, 'w') as file:
            json.dump({'log': {'entries': entries}, 'cleaned': True}, file, indent=2)
    else:
        print("File already preprocessed. Skipping.")
