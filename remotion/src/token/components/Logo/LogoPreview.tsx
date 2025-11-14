import React from 'react';
import { AbsoluteFill } from 'remotion';
import { Logo } from './Logo';

export const LogoPreview: React.FC = () => {
  return (
    <AbsoluteFill style={styles.container}>
      <div style={styles.content}>
        <Logo size={100} strokeWidth={10} color="#000000" />
      </div>
    </AbsoluteFill>
  );
};

// Styles
const styles = {
  container: {
    backgroundColor: '#f0f0f0',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  } as React.CSSProperties,
  content: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    gap: 20,
  },
};

