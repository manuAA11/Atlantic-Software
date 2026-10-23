import React from 'react';
import {View,Text} from 'react-native';
import {Button,color} from './ui';
export class Boundary extends React.Component<{children:React.ReactNode},{failed:boolean}>{
 state={failed:false};static getDerivedStateFromError(){return {failed:true};}
 render(){return this.state.failed?<View style={{flex:1,justifyContent:'center',padding:32,gap:20,backgroundColor:color.background}}><Text style={{fontSize:24,color:color.ink,fontWeight:'700'}}>Vamos a intentarlo de nuevo</Text><Text style={{color:color.muted}}>No se pudo mostrar esta pantalla. Tus registros guardados se conservan.</Text><Button label="Volver a abrir" onPress={()=>this.setState({failed:false})}/></View>:this.props.children;}
}
