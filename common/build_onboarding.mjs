import fs from 'node:fs';
import {signupHTML} from '../backend/core/onboarding.mjs';
const directory=new URL('../onboarding/',import.meta.url);
fs.mkdirSync(directory,{recursive:true});
const allowedBackends=['bawrakwhzkxmhmgkczqu','srmquhwpawgipncmvfjf'].map(id=>`https://${id}.supabase.co/functions/v1/marketing`);
fs.writeFileSync(new URL('index.html',directory),signupHTML({allowedBackends}));
console.log('Official authorization page generated; contains public configuration only.');
