import {defineConfig} from '@playwright/test';
export default defineConfig({
 testDir:'./tests/ui',timeout:45000,fullyParallel:false,workers:1,retries:0,
 use:{baseURL:'http://127.0.0.1:8765',viewport:{width:390,height:844},trace:'retain-on-failure'},
 webServer:{command:'python3 -m http.server 8765 --bind 127.0.0.1 --directory mobile/dist-web',url:'http://127.0.0.1:8765',reuseExistingServer:false},
 reporter:[['list'],['html',{open:'never',outputFolder:'.qa/browser-report'}]],
 outputDir:'.qa/browser-results',
});
