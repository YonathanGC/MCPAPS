document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('structuralCanvas')) {
        init3D();
    }
});

function init3D() {
    const canvas = document.getElementById('structuralCanvas');
    const container = canvas.parentElement;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    // Camera
    const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(10, 5, 20);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Controls
    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = false;
    controls.minDistance = 5;
    controls.maxDistance = 50;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 10, 7.5);
    scene.add(directionalLight);

    // Grid Helper
    const gridHelper = new THREE.GridHelper(50, 50);
    scene.add(gridHelper);

    // Materials
    const steelMaterial = new THREE.MeshStandardMaterial({ color: 0xcccccc, metalness: 0.8, roughness: 0.4 });
    const tensorMaterial = new THREE.MeshStandardMaterial({ color: 0xffaa00, metalness: 0.5, roughness: 0.6 });

    // Project Dimensions
    const claro = 16.5;
    const longitud = 27.4;
    const flecha = 1.8;
    const alturaArmadura = 0.45;
    const numMarcos = 6;
    const separacionMarcos = longitud / (numMarcos - 1);

    // Create a single parabolic truss
    function createParabolicTruss() {
        const group = new THREE.Group();

        // Parabolic curve for the top chord
        const curve = new THREE.CatmullRomCurve3([
            new THREE.Vector3(-claro / 2, 0, 0),
            new THREE.Vector3(-claro / 4, flecha, 0),
            new THREE.Vector3(0, flecha + alturaArmadura / 2, 0),
            new THREE.Vector3(claro / 4, flecha, 0),
            new THREE.Vector3(claro / 2, 0, 0)
        ]);

        const points = curve.getPoints(50);
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const topChord = new THREE.Line(geometry, steelMaterial);
        group.add(topChord);

        // Bottom chord (simplified as a straight line)
        const bottomChordGeom = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(-claro / 2, 0, 0),
            new THREE.Vector3(claro / 2, 0, 0)
        ]);
        const bottomChord = new THREE.Line(bottomChordGeom, steelMaterial);
        group.add(bottomChord);

        return group;
    }

    // Place trusses along the length
    for (let i = 0; i < numMarcos; i++) {
        const truss = createParabolicTruss();
        truss.position.z = i * separacionMarcos - longitud / 2;
        scene.add(truss);
    }

    // Add tensors (simplified)
    for (let i = 0; i < numMarcos - 1; i++) {
        const startZ = i * separacionMarcos - longitud / 2;
        const endZ = (i + 1) * separacionMarcos - longitud / 2;

        const tensorGeom1 = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(-claro / 4, flecha, startZ),
            new THREE.Vector3(claro / 4, flecha, endZ)
        ]);
        const tensor1 = new THREE.Line(tensorGeom1, tensorMaterial);
        scene.add(tensor1);

        const tensorGeom2 = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(claro / 4, flecha, startZ),
            new THREE.Vector3(-claro / 4, flecha, endZ)
        ]);
        const tensor2 = new THREE.Line(tensorGeom2, tensorMaterial);
        scene.add(tensor2);
    }

    // Data Visualization
    function visualizeStress() {
        scene.traverse((object) => {
            if (object.isLine) {
                const stress = Math.random(); // Simulated stress value (0 to 1)
                const color = new THREE.Color();
                color.setHSL(0.7 * (1 - stress), 1.0, 0.5); // Blue to Red gradient
                object.material = new THREE.LineBasicMaterial({ color: color });
            }
        });
    }

    // Add a button to trigger the visualization
    const stressButton = document.createElement('button');
    stressButton.textContent = 'Visualizar Esfuerzo';
    stressButton.style.position = 'absolute';
    stressButton.style.top = '10px';
    stressButton.style.left = '10px';
    stressButton.style.zIndex = '1';
    container.appendChild(stressButton);
    stressButton.addEventListener('click', visualizeStress);

    // Dynamic Geometry for Deflection
    let originalPositions = [];
    scene.traverse((object) => {
        if (object.isLine) {
            originalPositions.push(object.geometry.clone());
        }
    });

    function animateDeflection() {
        let i = 0;
        scene.traverse((object) => {
            if (object.isLine && i < originalPositions.length) {
                const original = originalPositions[i].attributes.position.array;
                const deflected = object.geometry.attributes.position.array;
                for (let j = 0; j < deflected.length; j += 3) {
                    const time = Date.now() * 0.001;
                    const deflection = Math.sin(j + time) * 0.1; // Simulated deflection
                    deflected[j + 1] = original[j + 1] - deflection;
                }
                object.geometry.attributes.position.needsUpdate = true;
                i++;
            }
        });
    }

    // Animation loop
    function animate() {
        requestAnimationFrame(animate);
        animateDeflection();
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }

    animate();

    // Handle window resize
    window.addEventListener('resize', () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
}
