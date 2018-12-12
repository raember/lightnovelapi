import json
import os

for filename in os.listdir("data"):
    print("Checking {}...".format(filename))
    if not filename.endswith('.har'):
        print("Not a HAR archive file. Skipping.")
        continue
    obj = {}
    with open(os.path.join('data', filename), 'r') as file:
        obj = json.load(file)
    if type(obj) == dict:
        print("Classified as unprocessed file. Cleaning...")
        entries = []
        for entry in obj['log']['entries']:
            request = entry['request']
            response = entry['response']
            entries.append({
                'request': {
                    'method': request['method'],
                    'url': request['url']
                },
                'response': {
                    'status': response['status'],
                    'content': response['content'],
                    'cookies': response['cookies'],
                    'redirectURL': response['redirectURL']
                }
            })
        print("Cleaned data. Making backup of old file. Writing back to disk.")
        os.rename(os.path.join('data', filename), os.path.join('data', filename + ".bak"))
        with open(os.path.join('data', filename), 'w') as file:
            json.dump(entries, file, indent=2)
    else:
        print("File already preprocessed. Skipping.")
