import type {ExpoConfig,ConfigContext} from 'expo/config';
export default ({config}:ConfigContext):ExpoConfig=>({
 ...config,
 name:'Atlantic League',
 slug:'atlantic-league',
 ...(process.env.EXPO_PUBLIC_EAS_PROJECT_ID?{extra:{eas:{projectId:process.env.EXPO_PUBLIC_EAS_PROJECT_ID}}}:{}),
});
