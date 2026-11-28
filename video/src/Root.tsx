import React from 'react';
import { Composition } from 'remotion';
import { Main, MainProps } from './Main';
import { TOTAL } from './timeline';

const defaultProps: MainProps = { bgm: true };

export const Root: React.FC = () => (
  <Composition
    id="LeadPilotDemo"
    component={Main}
    durationInFrames={TOTAL}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={defaultProps}
  />
);
