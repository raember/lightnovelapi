import json
import os

for filename in os.listdir("data"):
    print("Checking {}...".format(filename))
    if not filename.endswith('.har'):
        print("Not a HAR archive file. Skipping.")
        continue
    with open(os.path.join('data', filename), 'r') as file:
        obj = json.load(file)
    if type(obj) == dict:
        print("Classified as unprocessed file. Cleaning...")
        entries = []
        images = []
        for entry in obj['log']['entries']:
            request = entry['request']
            response = entry['response']
            respcontent = response['content']
            if 'mimeType' in respcontent:
                mimetype: str = respcontent['mimeType']
                if mimetype.startswith('image') and not request['url'] in images:
                    images.append(request['url'])
                elif mimetype.startswith('text/html'):
                    pass
                else:
                    continue
            else:
                continue
            headers = {}
            for header in response['headers']:
                headers[header['name']] = header['value']
            entries.append({
                'request': {
                    'method': request['method'],
                    'url': request['url']
                },
                'response': {
                    'status': response['status'],
                    'content': response['content'],
                    'cookies': response['cookies'],
                    'headers': headers,
                    'redirectURL': response['redirectURL']
                }
            })
        print("Cleaned data. Making backup of old file. Writing back to disk.")
        os.rename(os.path.join('data', filename), os.path.join('data', filename + ".bak"))
        with open(os.path.join('data', filename), 'w') as file:
            json.dump(entries, file, indent=2)
    else:
        print("File already preprocessed. Skipping.")
