 const usersChartCtx = document.getElementById('usersChart').getContext('2d');
    const gamesChartCtx = document.getElementById('gamesChart').getContext('2d');

    // График пользователей
    new Chart(usersChartCtx, {
        type: 'line',
        data: {
            labels: {{ user_dates|tojson|safe }},
            datasets: [{
                label: 'Новые пользователи',
                data: {{ user_counts|tojson|safe }},
                borderColor: '#6D5DFC',
                backgroundColor: 'rgba(109, 93, 252, 0.2)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: { color: '#fff' }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM D'
                        }
                    },
                    ticks: { color: '#fff' },
                    title: {
                        display: true,
                        text: 'Дата',
                        color: '#fff'
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#fff',
                        stepSize: 1
                    },
                    title: {
                        display: true,
                        text: 'Количество',
                        color: '#fff'
                    }
                }
            }
        }
    });

    // График игр
    new Chart(gamesChartCtx, {
        type: 'bar',
        data: {
            labels: {{ game_dates|tojson|safe }},
            datasets: [{
                label: 'Добавленные игры',
                data: {{ game_counts|tojson|safe }},
                backgroundColor: '#FF6F6F',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: { color: '#fff' }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM D'
                        }
                    },
                    ticks: { color: '#fff' },
                    title: {
                        display: true,
                        text: 'Дата',
                        color: '#fff'
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#fff',
                        stepSize: 1
                    },
                    title: {
                        display: true,
                        text: 'Количество',
                        color: '#fff'
                    }
                }
            }
        }
    });