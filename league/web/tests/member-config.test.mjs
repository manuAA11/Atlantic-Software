import test from 'node:test';
import assert from 'node:assert/strict';
import {memberEnvironment} from '../../backend/member-config.mjs';
import {createMemberAccessHandler} from '../../backend/member-access.mjs';
test('Cloudflare hosting adds its exact origin while preserving configured origins and pilot authorization',async()=>{
 const explicit={LEAGUE_WEB_ORIGINS:'https://existing.example',LEAGUE_PILOT_ONLY:'true'};
 const config=memberEnvironment({get:key=>explicit[key]});
 const origins=config.get('LEAGUE_WEB_ORIGINS').split(',');
 assert.deepEqual(origins,['https://existing.example','https://atlantic-league.atlanticsoftware11.workers.dev']);
 assert.equal(config.get('LEAGUE_PILOT_ONLY'),'true');
 assert.equal(config.get('UNCONFIGURED_SETTING'),undefined);
 const handler=createMemberAccessHandler({auth:{},store:{},pepper:'test-only-configuration-pepper-over-thirty-two-characters',allowedOrigins:origins});
 for(const allowed of origins){const response=await handler(new Request('https://api.example/access',{method:'OPTIONS',headers:{Origin:allowed}}));assert.equal(response.status,204);assert.equal(response.headers.get('Access-Control-Allow-Origin'),allowed);}
 const denied=await handler(new Request('https://api.example/access',{method:'OPTIONS',headers:{Origin:'https://untrusted.example.invalid'}}));
 assert.equal(denied.status,403);assert.equal(denied.headers.get('Access-Control-Allow-Origin'),null);
});
