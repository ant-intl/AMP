import { useState } from 'react';

interface Props {
  className: string;
  src: string;
  alt: string;
}

/** Product image that fades in over a placeholder background once loaded,
 *  preventing layout flicker during paced journey reveals. */
export default function FadeImg({ className, src, alt }: Props) {
  const [loaded, setLoaded] = useState(false);
  return (
    <img
      className={`${className} img-fade${loaded ? ' img-fade--loaded' : ''}`}
      src={src}
      alt={alt}
      onLoad={() => setLoaded(true)}
    />
  );
}
