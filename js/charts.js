document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('materialsChart')) {
        createMaterialsChart();
    }
    if (document.getElementById('costChart')) {
        createCostChart();
    }
});

function createMaterialsChart() {
    const ctx = document.getElementById('materialsChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Acero A-36', 'PTR 4x2', 'Lámina R-101', 'Tensores 3/8"'],
            datasets: [{
                label: 'Cantidad (kg)',
                data: [5500, 1200, 2000, 300],
                backgroundColor: 'rgba(0, 212, 255, 0.5)',
                borderColor: 'rgba(0, 212, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function createCostChart() {
    const ctx = document.getElementById('costChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Materiales', 'Mano de Obra', 'Maquinaria', 'Indirectos'],
            datasets: [{
                label: 'Distribución de Costos',
                data: [450000, 250000, 80000, 120000],
                backgroundColor: [
                    'rgba(0, 255, 136, 0.7)',
                    'rgba(0, 212, 255, 0.7)',
                    'rgba(255, 170, 0, 0.7)',
                    'rgba(255, 68, 68, 0.7)'
                ],
                hoverOffset: 4
            }]
        }
    });
}
