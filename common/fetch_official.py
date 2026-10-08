"""Fetch primary provider documentation for implementation review, never credentials."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
class Extract(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.out=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.skip=max(self.skip-1,0)
 def handle_data(self,data):
  if not self.skip and data.strip():self.out.append(data.strip())
root=Path(__file__).resolve().parents[1]/'research';root.mkdir(exist_ok=True)
urls={
 'meta_implementation':'https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/implementation/',
 'meta_versions':'https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/versions/',
 'meta_echoes':'https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/reference/smb_message_echoes/',
 'meta_onboard':'https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-tech-providers/',
 'meta_tokens':'https://developers.facebook.com/documentation/business-messaging/whatsapp/access-tokens/',
 'meta_webhook':'https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint/',
}
def fetch(item):
 key,url=item
 try:
  html=urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read().decode();e=Extract();e.feed(html)
  (root/(key+'.txt')).write_text(url+'\n\n'+'\n'.join(e.out));print(key,len(html),flush=True)
 except Exception as error:print(key,type(error).__name__,str(error),flush=True)
with ThreadPoolExecutor(4) as pool:list(pool.map(fetch,urls.items()))
