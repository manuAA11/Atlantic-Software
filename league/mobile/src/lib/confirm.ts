import {Alert,Platform} from 'react-native';
export function confirmAction(title:string,message:string,label:string,action:()=>void){
 if(Platform.OS==='web'){if(window.confirm(title+'\n\n'+message))action();return;}
 Alert.alert(title,message,[{text:'Cancelar',style:'cancel'},{text:label,onPress:action}]);
}
