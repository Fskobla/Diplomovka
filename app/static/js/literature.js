const descriptionContainers = document.querySelectorAll('.description-container');

descriptionContainers.forEach(container => {
    container.addEventListener('click', () => {
        const content = container.querySelector('.description-content');
        if (content.style.display === 'none' || content.style.display === '') {
            content.style.display = 'block';
            content.style.transition = 'ease-in 0.5s';
        } else {
            content.style.display = 'none';
            content.style.transition = 'ease-out 0.5s';
        }
    });
});

const keywordContainers = document.querySelectorAll('.keywords-container');

keywordContainers.forEach(container => {
    container.addEventListener('click', () => {
        const keywordsList = container.querySelector('.keywords-list');
        keywordsList.classList.toggle('show');
    });
});

const citationContainers = document.querySelectorAll('.citations-container');

citationContainers.forEach(container => {
    container.addEventListener('click', () => {
        const citationsList = container.querySelector('.citations-list');
        citationsList.classList.toggle('show');
    });
});