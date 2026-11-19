import {createConfiguredMemberHandler} from '../../../member-runtime.mjs';
import {memberEnvironment} from '../../../member-config.mjs';
Deno.serve(createConfiguredMemberHandler(memberEnvironment(Deno.env)));
