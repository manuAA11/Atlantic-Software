import {rmSync} from 'node:fs';
// Workers uses its own SPA routing; retain the shared Pages configuration in source.
rmSync(new URL('../web/dist/_redirects',import.meta.url),{force:true});
