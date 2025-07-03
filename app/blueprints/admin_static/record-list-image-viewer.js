$(document).ready(function() {

  // DOM element references
            const viewer = document.getElementById('viewer');
            const imageContainer = document.getElementById('image-container');
            const imageDisplay = document.getElementById('image-display');

            // Control buttons
            const zoomInBtn = document.getElementById('zoom-in');
            const zoomOutBtn = document.getElementById('zoom-out');
            const resetBtn = document.getElementById('reset-zoom');

            // State variables
            let scale = 1;
            let isPanning = false;
            let startX = 0;
            let startY = 0;
            let translateX = 0;
            let translateY = 0;

            // --- Utility Functions ---

            /**
             * Applies the current transform (scale and translate) to the image.
             */
            function applyTransform() {
                imageDisplay.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
            }

            /**
             * Resets the zoom and pan to the default state.
             */
            function resetTransform() {
                scale = 1;
                translateX = 0;
                translateY = 0;
                // Use the container's transition for a smooth reset
                imageContainer.style.transition = 'transform 0.3s ease-out';
                imageDisplay.style.transform = 'translate(0px, 0px) scale(1)';
                // Remove the smooth transition after it's done to allow for snappy dragging
                setTimeout(() => {
                    imageContainer.style.transition = 'none';
                }, 300);
            }

            // --- Event Handlers ---

            /**
             * Handles mouse wheel event for zooming.
             */
            viewer.addEventListener('wheel', (event) => {
                event.preventDefault(); // Prevent page scrolling

                const zoomIntensity = 0.1;
                const delta = event.deltaY > 0 ? -1 : 1; // -1 for zooming out, 1 for zooming in
                const newScale = scale + delta * zoomIntensity;
                
                // Clamp scale between min and max values
                scale = Math.min(Math.max(0.5, newScale), 5); 

                applyTransform();
            });

            /**
             * Handles the start of a pan action (mousedown or touchstart).
             */
            viewer.addEventListener('mousedown', (event) => {
                event.preventDefault();
                isPanning = true;
                // Record starting point relative to the viewport
                startX = event.clientX - translateX;
                startY = event.clientY - translateY;
                imageContainer.classList.add('grabbing');
            });

            viewer.addEventListener('touchstart', (event) => {
                event.preventDefault();
                isPanning = true;
                const touch = event.touches[0];
                startX = touch.clientX - translateX;
                startY = touch.clientY - translateY;
                imageContainer.classList.add('grabbing');
            });

            /**
             * Handles the panning action (mousemove or touchmove).
             */
            viewer.addEventListener('mousemove', (event) => {
                if (!isPanning) return;
                event.preventDefault();
                translateX = event.clientX - startX;
                translateY = event.clientY - startY;
                applyTransform();
            });

            viewer.addEventListener('touchmove', (event) => {
                if (!isPanning) return;
                event.preventDefault();
                const touch = event.touches[0];
                translateX = touch.clientX - startX;
                translateY = touch.clientY - startY;
                applyTransform();
            });

            /**
             * Handles the end of a pan action (mouseup, mouseleave, touchend).
             */
            const stopPanning = (event) => {
                if (isPanning) {
                    isPanning = false;
                    imageContainer.classList.remove('grabbing');
                }
            };
            window.addEventListener('mouseup', stopPanning);
            viewer.addEventListener('mouseleave', stopPanning);
            viewer.addEventListener('touchend', stopPanning);

            // --- Button Event Listeners ---
            zoomInBtn.addEventListener('click', () => {
                scale = Math.min(5, scale + 0.2);
                applyTransform();
            });

            zoomOutBtn.addEventListener('click', () => {
                scale = Math.max(0.5, scale - 0.2);
                applyTransform();
            });

  resetBtn.addEventListener('click', resetTransform);
});
