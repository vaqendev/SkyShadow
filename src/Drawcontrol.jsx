import { useControl } from "react-map-gl/maplibre";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import maplibregl from "maplibre-gl";

const customStyles = [
  // 1. ACTIVE (being drawn) - Fill
  {
    'id': 'gl-draw-polygon-fill-active',
    'type': 'fill',
    'filter': ['all', ['==', 'active', 'true'], ['==', '$type', 'Polygon']],
    'paint': {
        "fill-color": "#3bb2d0",
        'fill-opacity': 0
    }
  },
  // 2. ACTIVE (being drawn) - Stroke (Border)
  {
    'id': 'gl-draw-polygon-stroke-active',
    'type': 'line',
    'filter': ['all', ['==', 'active', 'true'], ['==', '$type', 'Polygon']],
    'paint': {
      'line-color': '#00FFFF',
      'line-dasharray': ["literal", [0.2, 2]], // Dashed line
      'line-width': 2
    }
  },
  // 3. INACTIVE (finished) - Fill
  {
    'id': 'gl-draw-polygon-fill-inactive',
    'type': 'fill',
    // 'filter': ['all', ['==', 'active', 'false'], ['==', '$type', 'Polygon']],
    "filter": ['all', ['==', 'active', 'false'], ['==', '$type', 'Polygon'], ['!=', 'mode', 'static']],
    "layout": {
      "line-cap": "round",
      "line-join": "round"
    },
    'paint': {
      'fill-color': '#3bb2d0', // Blue fill when done
      'fill-opacity': 0
    }
  },
  // 4. INACTIVE (finished) - Stroke
  {
    'id': 'gl-draw-polygon-stroke-inactive',
    'type': 'line',
    'filter': ['all', ['==', 'active', 'false'], ['==', '$type', 'Polygon']],
    'paint': {
      'line-color': '#00FFFF',
      'line-width': 2,
      "line-dasharray": ["literal", [0.2, 2]]
    }
  },
  // 5. VERTEX POINTS (The handles you drag)
  {
    'id': 'gl-draw-point-point-stroke-active',
    'type': 'circle',
    'filter': ['all', ['==', '$type', 'Point'], ['==', 'meta', 'vertex']],
    'paint': {
      'circle-radius': 7, // Make handles larger
      'circle-color': '#fff',
      'circle-stroke-color': '#00ffff',
      'circle-stroke-width': 2
    }
  }
];

export default function DrawControl(props){

    const {setPolygonControl, ref, ...defProps} = props;
    useControl(
        () => {
        // The "Secret Sauce": MapboxDraw expects mapboxgl, 
        // so we provide maplibregl in its place.
        const draw = new MapboxDraw({
            ...defProps,
            customStyles
        });
        // drawRef != null ? drawRef.current = draw : null;
        props.ref.current = draw;

        return draw;
        },
        ({ map }) => {
        map.on('draw.create', props.onCreate);
        map.on('draw.update', props.onUpdate);
        map.on('draw.delete', props.onDelete);
        },
        ({ map }) => {
        map.off('draw.create', props.onCreate);
        map.off('draw.update', props.onUpdate);
        map.off('draw.delete', props.onDelete);
        },
        {
        position: props.position
        }
    );

    return null;


};