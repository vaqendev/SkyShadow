import { useState, useCallback, useRef, useEffect } from 'react';
import './App.css';
import DrawControl from "./Drawcontrol";

import { PencilOff, SquareDashedMousePointer } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";

import { Card, CardHeader, CardDescription, CardTitle, CardFooter, CardContent } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

import styles from "./assets/App.module.css";
import 'mapbox-gl/dist/mapbox-gl.css';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';
import { DeckGL, GeoJsonLayer, ScatterplotLayer, HeatmapLayer, HexagonLayer, TileLayer, BitmapLayer, AmbientLight, PointLight, LightingEffect } from 'deck.gl';
import { MapboxOverlay as DeckOverlay } from '@deck.gl/mapbox';
import { Map, useControl, Marker } from "react-map-gl/maplibre";
import { Button, buttonVariants } from "@/components/ui/button";
import { center } from "@turf/center";
import area from "@turf/area";


const INITIAL_VIEW_STATE = {
  latitude: 28.6139,
  longitude: 77.2089,
  zoom: 6,
};

const MAPBOX_ACCESS_TOKEN = "pk.eyJ1Ijoienlnb3RlMTAwIiwiYSI6ImNtbDJscm96ZDBid2UzZnNkNzJ2cHptNjUifQ.CgyLlj3D28Sxh20MlhDGhw";
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

const TERRAIN_IMAGE = `https://api.mapbox.com/v4/mapbox.terrain-rgb/{z}/{x}/{y}.png?access_token=${MAPBOX_ACCESS_TOKEN}`;
const SURFACE_IMAGE = `https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}@2x.png?access_token=${MAPBOX_ACCESS_TOKEN}`;

const CARTO_DARK_STYLE = {
  version: 8,
  sources: {
    'carto-dark': {
      type: 'raster',
      tiles: [
        "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
        "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png"
      ],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap &copy; CARTO'
    }
  },
  layers: [
    {
      id: 'carto-dark-layer',
      type: 'raster',
      source: 'carto-dark',
      paint: {}
    }
  ]
};

function DeckGLOverlay(props) {
  const overlay = useControl(() => new DeckOverlay(props));
  overlay.setProps(props);
  return null;
}

const ambientLight = new AmbientLight({
  color: [255, 255, 255],
  intensity: 1.0
});

const pointLight1 = new PointLight({
  color: [255, 255, 255],
  intensity: 0.8,
  position: [77.1025, 28.802, 80000]
});

const pointLight2 = new PointLight({
  color: [255, 255, 255],
  intensity: 0.8,
  position: [-3.807751, 54.104682, 8000]
});

const lightingEffect = new LightingEffect({ambientLight, pointLight1});

function App() {

  const mapRef = useRef();
  const drawRef = useRef();
  const scanAnimationElement = useRef();
  const sliderRef = useRef(null);

  const [selected, setSelected] = useState(null);
  const [hoverInfo, setHoverInfo] = useState(null);
  const [polygonControlState, setPolygonControl] = useState(false);
  const [features, setFeatures] = useState({});
  const [areaAlert, setAreaAlert] = useState(false);
  const [placeResult, setPlaceResult] = useState([]);
  const [highlightedGeoJson, setHighlightedGeoJson] = useState(null);
  const [showMissionControl, setMissionControlView] = useState(false);
  const [tileLoaded, setTileLoaded] = useState(false);
  const [locationCenter, setLocationCenter] = useState(null);
  const [sliderValue, setSliderValue] = useState(0);

  const handleSearch = async function(e){
    if(e.key == "Enter"){
      const value = e.currentTarget.value;
      const searchText = value.replaceAll(" ", "+");
      setLocationCenter(null);
      setMissionControlView(false);
      setHighlightedGeoJson(null);
      
      try{
        const response = await fetch(`https://nominatim.openstreetmap.org/search.php?q=${searchText}&polygon_geojson=1&format=json`);
        if(!response.ok){
          throw new Error("Invalid url or something....");

        }
        const data = await response.json();
        console.log(data);
        await setPlaceResult(data);
        console.log(data.length);

      }catch(error){
        console.log(error);
      }

      console.log(placeResult);
    }
  }

  const performFreshView = (e) => {
    // console.log(drawRef);
    // drawRef.current.deleteAll();sop0oiplk;.,
    setAreaAlert(prev => !prev);
    setHighlightedGeoJson(null);
    setMissionControlView(false);
    setLocationCenter(null);
    // setPolygonControl(false);

  }
  

  const layers = [
    // new TileLayer({
    //   id: "TileLayer",
    //   //data: "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/cae4a54afdc6734ec7d7d44cff1a9e22-6925c060e298c439cba148dceae00061/tiles/{z}/{x}/{y}",
    //     //data: "https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/628598f88d0c8154fe1e9074e2130e80-8d43ed89a6b802c49b5847695b27d69b/tiles/{z}/{x}/{y}",
    //     data: "https://earthengine.googleapis.com/v1/projects/global-sun-484918-f5/maps/46ab6f24a82fcf7a2ce7dc6fae49e04d-9ae5e551c4220d68e0b4a0c819aa8e64/tiles/{z}/{x}/{y}",
    //   tileSize: 326,
    //   minZoom: 0,
    //   maxZoom: 19,
    //   opacity: 0.02,

    //   renderSubLayers: (props) => {
    //     const {
    //       bbox: { west, south, east, north }
    //     } = props.tile;

    //     return new BitmapLayer(props, {
    //       data: null,
    //       image: props.data,
    //       bounds: [west, south, east, north]
    //     });
    //   },
      
    //   pickable: true,
    //   onHover: info => setHoverInfo(info)
    // }),
    // new TileLayer({
    //     id: "TextLayer",
    //     data: "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    //     renderSubLayers: props => {
    //         const { bbox: { west, south, east, north } } = props.tile;
    //         return new BitmapLayer(props, {
    //             data: null,
    //             image: props.data,
    //             bounds: [west, south, east, north]
    //         });
    //     }
    // })
    // new ScatterplotLayer({
    //   id: "Scatter",
    //   data: dummyData,
    //   opacity: 0.8,
    //   filled: false,
    //   radiusMinPixels: 3,
    //   radiusMaxPixels: 11,
    //   getPosition: o => [o.longitude, o.latitude],
    //   getFillColor: o => o.risk_color,
    //   pickable: true,
    //   onHover: info => {console.log(info);setHoverInfo(info)},
    //   onclick: info => {
    //     setSelected(info);
    //     console.log(info);
    //   }
    //   // getFillColor: o => o.n_killed > 0 ? [255,0,0,255] : [170, 100, 0, 255]
    //   //o.properties.risk_color[0], o.properties.risk_color[1], o.properties.risk_color[2]
    // }),
    // new HeatmapLayer({
    //   id: "Heat",
    //   data: dummyData,
    //   getPosition: o => [o.longitude, o.latitude],
    //   getWeight: o => (o.temp/20) - o.ndvi,
    //   radiusPixels: 10,
    //   pickable: false,
    //   opacity: 0.2
    //   // onClick: (info) => {setSelected(info);},
      
    // }),
    new GeoJsonLayer({
      id: "GeoJsonLayer",
      data: highlightedGeoJson,
      filled: false,
      stroked: true,
      pickable: true,
      getLineColor: [255,255,255],
      getLineWidth: 10,
      lineWidthScale: 4,
      lineWidthMinPixels: 4,
      // getLineColor: [255, 10, 20, 255],
      getLineWidth: 20,
      getPointRadius: 4,
      getTextSize: 12
    }),
  ];


  const onUpdate = useCallback(e => {
    // THIS is your GeoJSON data
    const geojson = e.features[0];
    console.log(geojson);

    const calculatedArea = area(geojson.geometry);
    console.log("Calculated area is: ", calculatedArea);
    if((calculatedArea / 1000000) <= 1483){
      // allow the user to proceed.
      // load the tile.
      console.log("Loading the tile.");
    }else{
      setAreaAlert(true);
    }
    // console.log("Calculated area is: ", calculatedArea);
  }, []);

  const onDelete = useCallback(e => {
    console.log("Deleted features");
  }, []);

  const handleSearchItemClick = (e) => {
    console.log(e.target.id);
    console.log(placeResult[e.target.id]);
    const geojsonData = placeResult[e.target.id].geojson;
    console.log(geojsonData);
    var locationCenter = center(geojsonData);
    console.log("The location center is: ", locationCenter);

    scanAnimationElement.current.style.display = "block";
    setTimeout(() => scanAnimationElement.current.style.display = "none", 2500);

    setPlaceResult(null);

    setLocationCenter(locationCenter);
    setHighlightedGeoJson(geojsonData);
    setMissionControlView(true);

    mapRef.current.flyTo({
      center: locationCenter.geometry.coordinates,
      zoom: 10,
      duration: 2000,
      essential: true
    });

  }

  const handleSliderValueChange = (e) => {
    setSliderValue(e[0]);
  }

  const handleMissionControlClick = (e) => {

    const calculatedArea = area(highlightedGeoJson);
    if((calculatedArea / 1000000) <= 1483){
      // load the corresponding tile.
      console.log("Loading the corresponding tiles...");
      setTileLoaded(true);

    }else setAreaAlert(true);
    setMissionControlView(false);
  }

  return (
   <>
         <div id="scanner" ref={scanAnimationElement} className={styles.scanner}> <div className={styles.scan_line} /> </div>
         <Map
            ref={mapRef}
            initialViewState={INITIAL_VIEW_STATE}
            mapStyle={"https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"}>
            {polygonControlState && (
              <DrawControl
                ref={drawRef}
                position="top-left"
                displayControlsDefault={false}
                controls={{
                  polygon: true,
                  trash: true
                }}
                defaultMode="draw_polygon"
                onCreate={onUpdate}
                onUpdate={onUpdate}
                onDelete={onDelete}
                setPolygonControl={setPolygonControl}
              />
            )}
            <Card className={styles.hud_container}>
                <CardHeader>
                  <div className={styles.typography_container}>
                    <h1>Skyshadow</h1>
                    <h3>By TerrainByte</h3>
                  </div>
                  
                  <Input onKeyDown={handleSearch} className={styles.hero_input} placeholder="place" />
                  <div className={styles.search_place_container}>
                    {placeResult && (
                      placeResult.map((element, index) => (
                        <div id={index} key={index} onClick={handleSearchItemClick}>
                          {element.display_name}
                        </div>
                      ))
                    )}
                  </div>
                  
                  {/* <Button onClick={() => {setPolygonControl(prev => !prev);}} className={styles.polygon_toggle_button}>
                    <PencilOff strokeWidth={3} /> Polygon
                </Button> */}
                <CardTitle>Information Panel</CardTitle>
                <CardDescription className={styles.hud_description}>
                  Skyshadow with the help of carefully curated algorithms helps in the urban
                  plantation of tree 
                </CardDescription>
              </CardHeader>
              <CardContent>

                <div className="temp-container">
                  <h3>Temperature in the selected area is:</h3>
                  <h1>0°C</h1>
                </div> 
              </CardContent>
              <div className={styles.slider_container}>
                <h2 className={styles.slider_heading}>Vegetation Increase:<span className={styles.slider_heading_animate} /></h2>
                <div className={styles.slider_typo}>
                  <span id="slider-min">0%</span>
                  <span id="slider-present" className={styles.slider_val}>{sliderValue}%</span>
                  <span id="slider-max">30%</span>
                </div>

                <Slider onValueChange={handleSliderValueChange} disabled={!tileLoaded} className={styles.ndvi_slider} defaultValue={[0]} max={30} step={2} />    
              </div>
              <Button onClick={() => {setPolygonControl(prev => !prev)}} className={styles.define_target_btn}>
                Define Target Zone
              </Button>
            </Card>
            {showMissionControl && (
              <div className={styles.mission_control_container}>
                <h1 className={styles.mission_control_heading}>TARGET ACQUIRED</h1>
                <Button onClick={handleMissionControlClick} className={styles.mission_control_button}>
                  Analyse the whole region.
                </Button>
              </div>
            )}
            <div className={styles.alert_dialog}>
              <AlertDialog id="alert-dialog" className="area-alert-dialog" open={areaAlert}>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>
                      <SquareDashedMousePointer />
                    </AlertDialogTitle>
                    <AlertDialogDescription className={styles.alert_}>
                      <p className={styles.alert_caption}>Selected area is too big to analyse...</p>
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <Button className={styles.alert_button} onClick={performFreshView} variant="destructive">
                      Continue from fresh.
                    </Button>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
            <DeckGLOverlay layers={layers} /* interleaved*/ /> 
         </Map>
       </>
  )
}



export default App;

// {showMissionControl && (
//               <div className={styles.mission_control_container}>
//                 <h1>This is the mission control container</h1>
//               </div>
//             )}
