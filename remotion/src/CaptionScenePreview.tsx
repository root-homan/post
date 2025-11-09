import React from 'react';
import { AbsoluteFill } from 'remotion';
import { CaptionScene } from './CaptionScene';
import { CaptionData } from './types';

interface CaptionScenePreviewProps {
  inputProps: CaptionData;
}

/**
 * Preview wrapper for CaptionScene that adds a black background
 * so you can see the white captions in the browser preview.
 * 
 * The actual CaptionScene stays transparent for production renders.
 */
export const CaptionScenePreview: React.FC<CaptionScenePreviewProps> = ({ inputProps }) => {
  return (
    <>
      {/* Black background for preview only */}
      <AbsoluteFill style={styles.background} />
      
      {/* Actual caption scene (transparent) */}
      <CaptionScene inputProps={inputProps} />
    </>
  );
};

const styles = {
  background: {
    backgroundColor: '#000000',
    width: '100%',
    height: '100%',
  },
};

