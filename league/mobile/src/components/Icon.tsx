import React from 'react';
import {Ionicons} from '@expo/vector-icons';
import type {IconProps} from './Icon.types';
export type {IconName,IconProps} from './Icon.types';
export function Icon({name,size=22,color='#14283E'}:IconProps){
 return <Ionicons accessible={false} name={name} size={size} color={color}/>;
}
