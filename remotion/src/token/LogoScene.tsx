import React from 'react';
import { AbsoluteFill } from 'remotion';
import { Logo } from './components/Logo';

export const LogoScene: React.FC = () => {
  return (
    <AbsoluteFill style={styles.container}>
      <div style={styles.logoWrapper}>
        <Logo size={150} strokeWidth={15} color="#000000" />
      </div>
    </AbsoluteFill>
  );
};

// Styles
const styles = {
  container: {
    backgroundColor: '#ffffff',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  } as React.CSSProperties,
  logoWrapper: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  } as React.CSSProperties,
};

