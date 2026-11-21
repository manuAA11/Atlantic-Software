// Serve a non-redirecting root shell for service-worker precaching.
export default {
 fetch(request,env){
  const url=new URL(request.url);
  if(url.pathname!=='/')return env.ASSETS.fetch(request);
  if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405,headers:{Allow:'GET, HEAD','Cache-Control':'no-store'}});
  url.pathname='/index.html';url.search='';
  return env.ASSETS.fetch(new Request(url,{method:request.method,headers:{Accept:'text/html'}}));
 }
};
