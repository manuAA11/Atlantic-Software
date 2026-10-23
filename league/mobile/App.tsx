import React,{useEffect,useMemo,useState} from 'react';
import {ActivityIndicator,Linking,Pressable,Text,View} from 'react-native';
import {StatusBar} from 'expo-status-bar';
import {NavigationContainer,DefaultTheme} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import type {Session} from '@supabase/supabase-js';
import {Ionicons} from '@expo/vector-icons';
import type {RootStack,Tabs} from './src/navigation';
import {supabase,liveApi} from './src/lib/api';
import {demoApi} from './src/lib/demo';
import {secureStorage} from './src/lib/storage';
import {AthleteProvider,useAthlete} from './src/state/AthleteContext';
import {Boundary} from './src/components/Boundary';
import {color} from './src/components/ui';
import {AuthScreen} from './src/screens/AuthScreen';
import {DashboardScreen} from './src/screens/DashboardScreen';
import {TrainingScreen} from './src/screens/TrainingScreen';
import {GymScreen} from './src/screens/GymScreen';
import {LeagueScreen} from './src/screens/LeagueScreen';
import {AccountScreen} from './src/screens/AccountScreen';
import {WorkoutScreen} from './src/screens/WorkoutScreen';
import {StoryScreen} from './src/screens/StoryScreen';

const Stack=createNativeStackNavigator<RootStack>(),Tab=createBottomTabNavigator<Tabs>();
function Home(){
 return <Tab.Navigator screenOptions={({route})=>({headerShown:false,tabBarActiveTintColor:color.blue,tabBarInactiveTintColor:color.muted,tabBarStyle:{borderTopColor:color.line,backgroundColor:color.white,paddingTop:8},tabBarLabelStyle:{fontSize:10,fontWeight:'600'},tabBarIcon:({color:ink,size})=><Ionicons name={({'Inicio':'home-outline','Entrenar':'barbell-outline','Gimnasio':'business-outline','League':'podium-outline','Cuenta':'person-circle-outline'} as const)[route.name]} color={ink} size={size}/>})}>
  <Tab.Screen name="Inicio" component={DashboardScreen}/><Tab.Screen name="Entrenar" component={TrainingScreen}/><Tab.Screen name="Gimnasio" component={GymScreen}/><Tab.Screen name="League" component={LeagueScreen}/><Tab.Screen name="Cuenta" component={AccountScreen}/>
 </Tab.Navigator>;
}
function AthleteApp(){
 const {notice,setNotice,demo}=useAthlete();
 return <View style={{flex:1}}>
  {demo&&<View style={{backgroundColor:'#DDF5F6',padding:7,paddingTop:9}}><Text style={{fontSize:11,color:color.ink,textAlign:'center'}}>Demostración · Datos simulados · Sin conexión con gimnasios</Text></View>}
  <NavigationContainer theme={{...DefaultTheme,colors:{...DefaultTheme.colors,primary:color.blue,background:color.background,text:color.ink,border:color.line}}}>
   <Stack.Navigator screenOptions={{headerTintColor:color.ink,headerShadowVisible:false,headerStyle:{backgroundColor:color.background},contentStyle:{backgroundColor:color.background}}}>
    <Stack.Screen name="Home" component={Home} options={{headerShown:false}}/><Stack.Screen name="Workout" component={WorkoutScreen} options={{title:'Entrenamiento',presentation:'modal'}}/><Stack.Screen name="Story" component={StoryScreen} options={{title:'Crear historia'}}/>
   </Stack.Navigator>
  </NavigationContainer>
  {!!notice&&<Pressable accessibilityRole="alert" accessibilityLabel={notice} onPress={()=>setNotice('')} style={{position:'absolute',bottom:90,left:16,right:16,padding:16,borderRadius:16,backgroundColor:color.ink,elevation:5}}><Text style={{color:color.white,fontSize:14,lineHeight:20}}>{notice}</Text><Text style={{color:'#AFC8DB',fontSize:10,marginTop:5}}>Toca para cerrar</Text></Pressable>}
 </View>;
}
export default function App(){
 const [session,setSession]=useState<Session|null>(null),[ready,setReady]=useState(!supabase),[demo,setDemo]=useState(false),[recovery,setRecovery]=useState(false),demoClient=useMemo(demoApi,[]);
 useEffect(()=>{
  if(!supabase)return;let active=true;
  supabase.auth.getSession().then(({data})=>{if(active){setSession(data.session);setReady(true);}}).catch(()=>{if(active)setReady(true);});
  const {data:{subscription}}=supabase.auth.onAuthStateChange((event,value)=>{if(active){setSession(value);if(event==='PASSWORD_RECOVERY')setRecovery(true);}});
  return()=>{active=false;subscription.unsubscribe();};
 },[]);
 useEffect(()=>{
  const open=async(url:string)=>{
   try{const link=new URL(url);if(link.protocol!=='atlanticleague:')return;
    const token=link.searchParams.get('token');if(token&&/^[a-f0-9]{64}$/.test(token))await secureStorage.setItem('league-activation',token);
    const code=link.searchParams.get('code');if(code&&supabase){const {error}=await supabase.auth.exchangeCodeForSession(code);if(error)throw error;}
   }catch{/* Never expose auth URLs in logs. */}
  };
  void Linking.getInitialURL().then(url=>{if(url)void open(url);});const subscription=Linking.addEventListener('url',event=>void open(event.url));return()=>subscription.remove();
 },[]);
 return <SafeAreaProvider><Boundary><StatusBar style="dark"/>{!ready?<View style={{flex:1,justifyContent:'center',backgroundColor:color.background}}><ActivityIndicator color={color.blue}/></View>:recovery||(!session&&!demo)?<AuthScreen recovery={recovery} onRecovered={()=>setRecovery(false)} onDemo={()=>setDemo(true)}/>:<AthleteProvider key={demo?'demo':session!.user.id} userId={demo?'demo':session!.user.id} demo={demo} api={demo?demoClient:liveApi} signOut={async()=>{if(demo)setDemo(false);else await supabase!.auth.signOut();}}><AthleteApp/></AthleteProvider>}</Boundary></SafeAreaProvider>;
}
