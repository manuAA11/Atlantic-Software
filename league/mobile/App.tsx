import React,{useEffect,useMemo,useState} from 'react';
import {ActivityIndicator,Image,Linking,Pressable,Text,View} from 'react-native';
import {StatusBar} from 'expo-status-bar';
import {NavigationContainer,DefaultTheme,DarkTheme} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {SafeAreaProvider,useSafeAreaInsets} from 'react-native-safe-area-context';
import type {Session} from '@supabase/supabase-js';
import {Icon} from './src/components/Icon';
import {Viewport} from './src/components/Viewport';
import type {RootStack,Tabs} from './src/navigation';
import {supabase,liveApi,signOutCurrentSession} from './src/lib/api';
import {demoApi} from './src/lib/demo';
import {secureStorage} from './src/lib/storage';
import {AthleteProvider,useAthlete} from './src/state/AthleteContext';
import {PwaStatus} from './src/components/PwaStatus';
import {Platform} from 'react-native';
import {Boundary} from './src/components/Boundary';
import {useUi} from './src/components/ui';
import {ThemeProvider} from './src/components/Theme';
import {BrandHeader} from './src/components/BrandHeader';
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
 const insets=useSafeAreaInsets(),{color}=useUi();
 return <View style={{flex:1,minHeight:0}}><Tab.Navigator screenOptions={({route})=>({headerShown:true,header:({navigation})=><BrandHeader onProfile={()=>navigation.navigate('Cuenta')}/>,tabBarActiveTintColor:color.blue,tabBarInactiveTintColor:color.muted,tabBarLabelPosition:'below-icon',tabBarStyle:{borderTopColor:color.line,backgroundColor:color.surface,height:62+Math.max(insets.bottom,8),paddingTop:6,paddingBottom:Math.max(insets.bottom,8),flexShrink:0},tabBarItemStyle:{minWidth:0,paddingHorizontal:2},tabBarLabelStyle:{fontSize:11,lineHeight:15,fontWeight:'600'},tabBarIcon:({color:ink,size})=><Icon name={({'Inicio':'home-outline','Entrenar':'barbell-outline','Gimnasio':'calendar-outline','League':'trophy-outline','Cuenta':'person-circle-outline'} as const)[route.name]} color={ink} size={size}/>})}>
  <Tab.Screen name="Inicio" component={DashboardScreen}/><Tab.Screen name="League" component={LeagueScreen}/><Tab.Screen name="Gimnasio" component={GymScreen} options={{tabBarLabel:'Agenda',title:'Agenda'}}/><Tab.Screen name="Entrenar" component={TrainingScreen} options={{tabBarLabel:'Rutinas',title:'Rutinas'}}/><Tab.Screen name="Cuenta" component={AccountScreen} options={{tabBarLabel:'Perfil',title:'Perfil'}}/>
 </Tab.Navigator></View>;
}
function AthleteApp(){
 const {notice,setNotice,demo}=useAthlete();
 const {color,dark}=useUi();
 return <View style={{flex:1,minHeight:0}}>
  {demo&&<View style={{backgroundColor:color.soft,padding:7,paddingTop:9}}><Text style={{fontSize:11,color:color.ink,textAlign:'center'}}>Demostración · Datos simulados · Sin conexión con gimnasios</Text></View>}
  <NavigationContainer theme={{...(dark?DarkTheme:DefaultTheme),colors:{...(dark?DarkTheme:DefaultTheme).colors,primary:color.blue,background:color.background,text:color.ink,border:color.line,card:color.surface}}}>
   <Stack.Navigator screenOptions={{headerTintColor:color.ink,headerShadowVisible:false,headerStyle:{backgroundColor:color.background},contentStyle:{backgroundColor:color.background}}}>
    <Stack.Screen name="Home" component={Home} options={{headerShown:false}}/><Stack.Screen name="Workout" component={WorkoutScreen} options={{title:'Entrenamiento',presentation:'modal'}}/><Stack.Screen name="Story" component={StoryScreen} options={{title:'Crear historia'}}/>
   </Stack.Navigator>
  </NavigationContainer>
  {!!notice&&<Pressable accessibilityRole="alert" accessibilityLabel={notice} onPress={()=>setNotice('')} style={{position:'absolute',bottom:90,left:16,right:16,padding:16,borderRadius:16,backgroundColor:dark?'#203A56':'#192F46',elevation:5}}><Text style={{color:color.white,fontSize:14,lineHeight:20}}>{notice}</Text><Text style={{color:'#AFC8DB',fontSize:10,marginTop:5}}>Toca para cerrar</Text></Pressable>}
 </View>;
}
function LeagueApp(){
 const {color,dark}=useUi();
 const [session,setSession]=useState<Session|null>(null),[ready,setReady]=useState(!supabase),[demo,setDemo]=useState(false),[recovery,setRecovery]=useState(false),demoClient=useMemo(demoApi,[]);
 useEffect(()=>{
  if(!supabase)return;let active=true;
  supabase.auth.getSession().then(({data})=>{if(active){setSession(data.session);setReady(true);}}).catch(()=>{if(active)setReady(true);});
  const {data:{subscription}}=supabase.auth.onAuthStateChange((event,value)=>{if(active){setSession(value);if(event==='PASSWORD_RECOVERY')setRecovery(true);}});
  return()=>{active=false;subscription.unsubscribe();};
 },[]);
 useEffect(()=>{
  const open=async(url:string)=>{
   try{const link=new URL(url);if(Platform.OS==='web'?(link.origin!==window.location.origin):link.protocol!=='atlanticleague:')return;
    const token=link.searchParams.get('token');if(token&&/^[a-f0-9]{64}$/.test(token)){await secureStorage.setItem('league-activation',token);if(Platform.OS==='web'){const clean=new URL(window.location.href);clean.searchParams.delete('token');window.history.replaceState({},'',clean.pathname+clean.search+clean.hash);}}
    const code=link.searchParams.get('code');if(code&&supabase){const {error}=await supabase.auth.exchangeCodeForSession(code);if(error)throw error;if(Platform.OS==='web'){const clean=new URL(window.location.href);clean.searchParams.delete('code');clean.searchParams.delete('token');window.history.replaceState({},'',clean.pathname+clean.search+clean.hash);}}
   }catch{/* Never expose auth URLs in logs. */}
  };
  void Linking.getInitialURL().then(url=>{if(url)void open(url);});const subscription=Linking.addEventListener('url',event=>void open(event.url));return()=>subscription.remove();
 },[]);
 return <SafeAreaProvider style={{flex:1,minHeight:0}}><Boundary><Viewport/><PwaStatus/><StatusBar style={dark?'light':'dark'}/>{!ready?<View style={{flex:1,justifyContent:'center',backgroundColor:color.background}}><ActivityIndicator color={color.blue}/></View>:recovery||(!session&&!demo)?<AuthScreen recovery={recovery} onRecovered={()=>setRecovery(false)} onDemo={()=>setDemo(true)}/>:<AthleteProvider key={demo?'demo':session!.user.id} userId={demo?'demo':session!.user.id} demo={demo} api={demo?demoClient:liveApi} signOut={async()=>{if(demo)setDemo(false);else await signOutCurrentSession();}}><AthleteApp/></AthleteProvider>}</Boundary></SafeAreaProvider>;
}

export default function App(){return <ThemeProvider><LeagueApp/></ThemeProvider>;}
