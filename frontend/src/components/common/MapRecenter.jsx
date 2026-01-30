import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

export function MapRecenter({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView([center.lat, center.lng], 13);
    }
  }, [center, map]);
  return null;
}
