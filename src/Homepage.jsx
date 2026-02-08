import { useEffect } from "react";
import styles from "../src/assets/Home.module.css";
import { Link } from "react-router-dom";

export default function Homepage(){

    useEffect(() => {
          const heroTitle = document.getElementById('heroTitle');
        const mainInterface = document.getElementById('mainInterface');
        const mainSlider = document.getElementById('mainSlider');
        const fixedNav = document.getElementById('fixedNav');
        const progress = document.getElementById('progress');
        const streamLine = document.getElementById('streamLine');

        // 1. INITIALIZATION 
        // Force scroll to top on reload to ensure animation sequence starts correctly
        window.addEventListener('load', () => { 
            if (window.scrollY > 10) {
                window.scrollTo(0, 0);
            }
        });

        // 2. SCROLL ENGINE
        window.addEventListener('scroll', () => {
            const y = window.scrollY;
            const viewHeight = window.innerHeight;

            // A. HEADER DOCKING & SLIDER REVEAL
            // Trigger: As soon as user starts scrolling
            if (y > 50) {
                heroTitle.classList.add('docked');
                mainInterface.classList.add('active');
                fixedNav.style.opacity = 1;
            } else {
                heroTitle.classList.remove('docked');
                mainInterface.classList.remove('active');
                fixedNav.style.opacity = 0;
            }

            // B. DATA STREAM LINE 
            // Trigger: Only visible when scrolling between Intro and Vertical content
            if (y > viewHeight * 0.8 && y < viewHeight * 1.5) {
                streamLine.style.opacity = 1;
                streamLine.style.height = (y - viewHeight * 0.5) + 'px'; // Dynamic growth
            } else {
                streamLine.style.opacity = 0;
            }

            // C. TEXT REVEAL LOGIC
            const text = document.getElementById('revealText');
            const spans = text.querySelectorAll('span');
            const rect = text.getBoundingClientRect();

            // Reveal starts when text enters bottom 80% of screen
            if (rect.top < viewHeight * 0.85) {
                const scrolled = Math.max(0, (viewHeight * 0.85) - rect.top);
                const maxScroll = viewHeight * 0.5; 
                const percentage = Math.min(1, scrolled / maxScroll);
                const activeCount = Math.floor(percentage * spans.length);
                
                spans.forEach((span, idx) => {
                    if (idx <= activeCount) span.classList.add('active');
                    else span.classList.remove('active');
                });
            }
        });

        // 3. HORIZONTAL SLIDER LOGIC
        mainSlider.addEventListener('scroll', () => {
            const maxScroll = mainSlider.scrollWidth - mainSlider.clientWidth;
            const scrollPercentage = mainSlider.scrollLeft / maxScroll;
            progress.style.left = (scrollPercentage * 66.66) + '%';
        });

        function scrollToSlide(index) {
            mainSlider.scrollTo({ 
                left: window.innerWidth * index, 
                behavior: 'smooth' 
            });
        }
    })

    return(
        <div className={styles.home_wrapper}>
            <div className="stars"></div>
    
      <div className="intro-track">
        
        <div className="sticky-wrapper">
            
            <div className="hero-container" id="heroTitle">
                <h1 id="Projectname">SKYSHADOW</h1>
                <p id="a">Orchestrating Urban Cooling via Satellite Synthesis</p>
            </div>
            <div className="scroll-hint">SCROLL TO INITIALIZE SYSTEM</div>

            <div className="scroll-nav" id="fixedNav">
                <div className="nav-bar">
                    <div className="nav-progress" id="progress"></div>
                    {/* Fixed onClick syntax */}
                    <button onClick={() => scrollToSlide(0)}></button>
                    <button onClick={() => scrollToSlide(1)}></button>
                    <button onClick={() => scrollToSlide(2)}></button>
                </div>
            </div>

            <div className="main-interface" id="mainInterface">
                <div className="horizontal-slider" id="mainSlider">
                    
                    <section className="slide">
                        <div className="slide-bg"><div className="grid-layer"></div></div>
                        <div className="hook">
                            <div className="titles"><h3 id="how">How it Works?</h3></div>
                            <div className="subheading"><p><b>Beyond Observation:</b> Environmental Data Synthesis. We leverage Landsat 8/9 thermal infrared sensors and Sentinel-2 optical data to create a unified environmental grid.</p></div>
                        </div>
                    </section>

                    <section className="slide">
                        <div className="slide-bg heat-map"></div>
                        <div className="hook">
                            <div className="titles"><h3 id="ab">THE HOOK</h3></div>
                            <div className="subheading"><p>SkyShadow merges multi-spectral satellite imagery with geospatial mathematics to identify "Red Zones." We provide city planners with precise data to engineer a cooler future.</p></div>
                        </div>
                    </section>

                    <section className="slide">
                        <div className="slide-bg bio-veins"></div>
                        <div className="hook">
                            <div className="titles"><h3 id="MISSION">MISSION</h3></div>
                            <div className="subheading"><p>Urban Heat Islands are public health crises. We provide the infrastructure to close the "cooling gap," empowering municipalities to build life-sustaining green corridors.</p></div>
                        </div>
                    </section>
                </div>
            </div>
        
        </div>
      </div> 
      
      {/* NOTE: I removed the extra </div> tags that were here. 
         This allows the code below to be "reachable".
      */}

      <div className="data-stream-line" id="streamLine"></div>

      <div className="vertical-section" id="verticalContent">
        
        <div className="reveal-container">
            <div className="reveal-text" id="revealText">
                <span>The Urban Heat Crisis is invisible.</span>
                <span>Concrete traps heat.</span>
                <span>Temperatures rise 5°C.</span>
                <span>Cities are suffocating.</span>
                <span>Vulnerable populations are at risk.</span>
                <span>Energy demands are spiking.</span>
                <span className="final-line">We need a new lens.</span>
            </div>
        </div>

        <div className="bento-section">
            <div className="bento-header">
                <span className="mono-tag">TECHNICAL SPECIFICATIONS</span>
                <h2 className="bento-main-title">The Digital Twin Engine.</h2>
            </div>
            <div className="bento-grid">
                <div className="bento-box">
                    <div className="glow-spot"></div>
                    <div>
                        <div className="bento-num">30m</div>
                        <div className="bento-title">Spatial Precision</div>
                    </div>
                    <p className="bento-desc">Granular analysis down to individual city blocks using fused Sentinel-2 optical grids.</p>
                </div>
                <div className="bento-box">
                    <div className="glow-spot"></div>
                    <div>
                        <div className="bento-num">&lt;10s</div>
                        <div className="bento-title">Analysis Latency</div>
                    </div>
                    <p className="bento-desc">Real-time computation pipeline powered by Google Earth Engine distributed cloud clusters.</p>
                </div>
                <div className="bento-box bento-wide">
                    <div className="glow-spot"></div>
                    <div className="bento-wide-content">
                        <div className="bento-num">L8+L9</div>
                        <div className="bento-title">Multi-Spectral Fusion</div>
                    </div>
                    <p className="bento-desc">We merge Landsat 8 and 9 thermal data to pierce through atmospheric interference, ensuring 100% data availability.</p>
                </div>
            </div>
        </div>

        <section className="footer-section">
            <div className="footer-tag">SDG 13 • CLIMATE ACTION</div>
            {/* Fixed self-closing <br /> tag */}
            <h1 className="footer-title">Build the cities of<br />tomorrow, today.</h1>
            
            {/* Note: If you are using React Router, change <a href> to <Link to> 
               Otherwise, a standard anchor tag is fine.
            */}
            <Link to="/app" className="launch-btn">Launch Thermal Engine</Link>
            
            <div className="version-text">v1.0.4 - Connected to Earth Engine</div>
            
            <div className="footer-copy">TERRAINBYTE © 2026. All Systems Nominal.<br />Powered by Google Earth Engine.</div>
        </section>
    </div>
    
    
        </div>        
        
    )
}