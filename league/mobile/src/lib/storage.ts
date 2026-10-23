import {Platform} from 'react-native';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';
import {chunkStorage} from './chunk-storage';
const memory=new Map<string,string>();
const base=Platform.OS==='web'?{
 getItem:async(key:string)=>memory.get(key)||null,
 setItem:async(key:string,value:string)=>{memory.set(key,value);},
 removeItem:async(key:string)=>{memory.delete(key);},
}:{
 getItem:(key:string)=>SecureStore.getItemAsync(key),
 setItem:(key:string,value:string)=>SecureStore.setItemAsync(key,value,{keychainAccessible:SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY}),
 removeItem:(key:string)=>SecureStore.deleteItemAsync(key),
};
export const secureStorage=chunkStorage(base,()=>Crypto.randomUUID());
