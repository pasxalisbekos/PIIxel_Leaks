import json

with open('pixels_found.json','r') as f:
    data = json.load(f)
    print(len(data))
f.close()

with open('state_fbq.json','r') as f:
    data = json.load(f) 
    print(len(data))
f.close()
