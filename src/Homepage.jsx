// <!DOCTYPE html>
// <html lang="en">
// <head>
//     <meta charset="UTF-8">
//     <meta name="viewport" content="width=device-width, initial-scale=1.0">
//     <title>SkyShadow: Direct Focus</title>
//     <style>
//         body, html {
//             margin: 0;
//             padding: 0;
//             width: 100%;
//             height: 100%;
//             /* Deep Void Background */
//             background-color: #030510;
//             overflow: hidden;
//             font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
//             display: flex;
//             justify-content: center;
//             align-items: center;
//         }

//         #container {
//             position: relative;
//             width: 100vw;
//             height: 100vh;
//             display: flex;
//             justify-content: center;
//             align-items: center;
//         }

//         /* --- THE MAP OBJECT --- */
//         #world-map {
//             /* 1. START STATE: Sphere */
//             width: 300px;
//             height: 300px;
//             border-radius: 50%;
            
//             background-image: url('https://upload.wikimedia.org/wikipedia/commons/c/cd/Land_ocean_ice_2048.jpg');
            
//             /* Sizing for seamless rotation (2x width) */
//             background-size: 200% 100%;
//             background-repeat: repeat-x;
//             background-position: 0 50%;

//             /* THEME: Dark Purple/Blue Satellite */
//             filter: grayscale(100%) contrast(140%) brightness(90%) sepia(100%) hue-rotate(230deg) saturate(350%);
            
//             /* 3D Shadows */
//             box-shadow: inset 40px 0 80px 10px rgba(0,0,0,1), 
//                         0 0 60px rgba(100, 50, 255, 0.5);
            
//             position: absolute;
//             z-index: 1;

//             /* UNIFIED TRANSITION: 
//                Everything happens over 3 seconds with a smooth ease-in-out curve.
//             */
//             transition: width 3s cubic-bezier(0.45, 0, 0.55, 1),
//                         height 3s cubic-bezier(0.45, 0, 0.55, 1),
//                         border-radius 3s cubic-bezier(0.45, 0, 0.55, 1),
//                         background-size 3s cubic-bezier(0.45, 0, 0.55, 1),
//                         background-position 3s cubic-bezier(0.45, 0, 0.55, 1),
//                         box-shadow 3s ease;
//         }

//         /* ROTATION ANIMATION */
//         .rotating {
//             animation: rotateGlobe 4s linear infinite;
//         }

//         @keyframes rotateGlobe {
//             from { background-position: 0 50%; }
//             to { background-position: -200% 50%; } 
//         }

//         /* 2. FINAL STATE: Expanded AND Focused on India */
//         #world-map.expanded {
//             /* Full Screen Dimensions */
//             width: 100vw;
//             height: 100vh;
//             border-radius: 0;
            
//             /* Vignette shadow instead of sphere shadow */
//             box-shadow: inset 0 0 300px rgba(0,0,0,1); 
            
//             /* ZOOM & COORDINATES DIRECTLY APPLIED HERE */
//             /* We zoom in to 400% size immediately during expansion */
//             background-size: 400% 400%; /* Height scales with width now for zoom */
            
//             /* Coordinates for India centered */
//             background-position: 72% 40%;
//         }

//         /* --- TEXT OVERLAY --- */
//         .text-overlay {
//             position: absolute;
//             z-index: 2;
//             text-align: left;
//             color: white;
//             opacity: 0;
//             transform: translateY(30px);
//             transition: opacity 1.5s ease, transform 1.5s ease;
//             pointer-events: none;
            
//             background: rgba(12, 12, 30, 0.85);
//             padding: 40px;
//             border-left: 5px solid #bd00ff;
//             backdrop-filter: blur(12px);
//             box-shadow: 0 30px 60px rgba(0,0,0,0.8);
//             border-radius: 0 20px 20px 0;
//         }

//         .text-overlay h2 {
//             font-size: 1.2rem;
//             text-transform: uppercase;
//             letter-spacing: 4px;
//             color: #bd00ff;
//             margin: 0 0 10px 0;
//             text-shadow: 0 0 15px rgba(189, 0, 255, 0.6);
//         }

//         .text-overlay h1 {
//             font-size: 4rem;
//             margin: 0;
//             font-weight: 800;
//             line-height: 1;
//             margin-bottom: 20px;
//             color: #ffffff;
//         }

//         .text-overlay p {
//             font-size: 1.3rem;
//             color: #c0c0ff;
//             max-width: 550px;
//             line-height: 1.6;
//             margin: 0;
//         }

//         .text-overlay.visible {
//             opacity: 1;
//             transform: translateY(0);
//         }
//     </style>
// </head>
// <body>

//     <div id="container">
//         <div id="world-map" class="rotating"></div>
        
//         <div class="text-overlay" id="message">
//             <h2>SkyShadow</h2>
//             <h1>Global Heat<br>Analysis</h1>
//             <p><strong>Target Acquired:</strong> India Sector.<br>
//             Satellite thermal scanning complete. Urban Heat Island data ready for processing.</p>
//         </div>
//     </div>

//     <script>
//         const map = document.getElementById('world-map');
//         const text = document.getElementById('message');

//         // TIMELINE
        
//         // 1. Spin for 5 seconds
//         setTimeout(() => {
//             transitionToIndia();
//         }, 5000);

//         function transitionToIndia() {
//             // A. FREEZE ROTATION
//             // Get current computed position to prevent snapping
//             const computedStyle = window.getComputedStyle(map);
//             const currentBgPos = computedStyle.getPropertyValue('background-position');
            
//             map.classList.remove('rotating');
//             map.style.backgroundPosition = currentBgPos;
            
//             // Force browser update
//             void map.offsetWidth;

//             // B. EXPAND & FOCUS (Combined Step)
//             // We set a tiny timeout to allow the 'style' removal to register
//             // so the CSS class takes over seamlessly.
//             setTimeout(() => {
//                 map.style.backgroundPosition = ''; // Remove inline style so class takes over
//                 map.classList.add('expanded'); // Triggers width, height, AND zoom to India
//             }, 50);
//         }

//         // 2. SHOW TEXT (After the 3s expansion finishes)
//         setTimeout(() => {
//             text.classList.add('visible');
//         }, 8100); // 5000 (spin) + 3000 (expand) + buffer

//     </script>
// </body>
// </html>