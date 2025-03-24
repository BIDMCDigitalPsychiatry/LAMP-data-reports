document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('textForm');
    const responseMessage = document.getElementById('responseMessage');
    let lastHtmlResponse = null; // Store the last HTML response

    // Create the retry button (outside of event listener)
    const retryButton = document.createElement('button');
    retryButton.style.marginTop = '10px';
    retryButton.style.padding = '8px 16px';
    retryButton.style.fontSize = '16px';
    retryButton.style.cursor = 'pointer';
    retryButton.style.border = 'none';
    retryButton.style.background = '#007bff';
    retryButton.style.color = 'white';
    retryButton.style.borderRadius = '5px';
    retryButton.style.textAlign = 'center';
    retryButton.style.position = 'relative';
    retryButton.style.left = '50%';
    retryButton.style.transform = 'translateX(-50%)';
    retryButton.onclick = function () {
        if (lastHtmlResponse) {
            const newTab = window.open();
            if (newTab) {
                newTab.document.write(lastHtmlResponse);
                newTab.document.close();
                retryButton.style.display = 'none'; 
            } else {
                responseMessage.textContent = 'Pop-up blocked again. Please check your browser settings.';
            }
        }
    };

    
    responseMessage.parentNode.insertBefore(retryButton, responseMessage.nextSibling);

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        responseMessage.textContent = 'Generating report... Please wait.';
        retryButton.style.display = 'none'; 

        const formData = new FormData(form);

        fetch('/generate', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(errorMsg => {
                    throw new Error(errorMsg || 'Report generation failed');
                });
            }

            const contentType = response.headers.get('content-type');

            if (contentType.includes('text/html')) {
                return response.text().then(html => {
                    const newTab = window.open();
                    if (newTab) {
                        newTab.document.write(html);
                        newTab.document.close();
                        responseMessage.textContent = 'HTML report generated successfully!';
                    } else {
                        lastHtmlResponse = html; 
                        responseMessage.textContent = 'Pop-up blocked. Click "Retry" to open the report.';
                        retryButton.style.display = 'inline-block'; 
                    }
                });
            } else {
                throw new Error('Unexpected response format');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            responseMessage.textContent = 'Error: ' + error.message;
            if (lastHtmlResponse) {
                retryButton.style.display = 'inline-block';
            }
        });
    });
});
