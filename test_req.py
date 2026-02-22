import requests
import re

try:
    s = requests.Session()
    r = s.get('http://127.0.0.1:5000/register')
    print('GET /register:', r.status_code)
    
    match = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    token = match.group(1) if match else ''
    print("Found CSRF Token:", token)
    
    data = {'username': 'testuser123', 'password': 'password123', 'csrf_token': token}
    r2 = s.post('http://127.0.0.1:5000/register', data=data, allow_redirects=False)
    print('POST /register status:', r2.status_code)
    print('POST /register headers:', r2.headers)
    if 'danger' in r2.text or r2.status_code != 302:
        print('Error text:', r2.text[:300])
except Exception as e:
    print('Error:', e)
