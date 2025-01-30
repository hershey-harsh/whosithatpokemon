document.querySelectorAll('pre').forEach(pre => {
    const button = document.createElement('button');
    button.className = 'copy-btn absolute top-2 right-2 bg-gray-200 px-2 py-1 rounded text-sm';
    button.textContent = 'Copy';
    
    button.addEventListener('click', () => {
        const text = pre.querySelector('code').textContent;
        navigator.clipboard.writeText(text);
        button.textContent = 'Copied!';
        setTimeout(() => button.textContent = 'Copy', 2000);
    });
    
    pre.style.position = 'relative';
    pre.appendChild(button);
});