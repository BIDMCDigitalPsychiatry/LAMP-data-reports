document.addEventListener('DOMContentLoaded', function() {
    // Get the form element
    const form = document.getElementById('textForm');
    const responseMessage = document.getElementById('responseMessage');
    
    // Add event listener for form submission
    form.addEventListener('submit', function(event) {
        // Prevent the default form submission
        event.preventDefault();
        
        // Show loading message
        responseMessage.textContent = 'Generating report... Please wait.';
        
        // Create a FormData object to easily send form data
        const formData = new FormData(form);
        
        // Send AJAX request
        fetch('/generate', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            // Check if the response is successful
            if (!response.ok) {
                // If we get a JSON error response, parse it
                if (response.headers.get('content-type')?.includes('application/json')) {
                    return response.json().then(data => {
                        throw new Error(data.error || 'Report generation failed');
                    });
                }
                throw new Error('Report generation failed with status: ' + response.status);
            }
            
            // Check the content type of the response
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/pdf')) {
                // For PDF: Create a blob and open it in a new tab
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    window.open(url, '_blank');
                    responseMessage.textContent = 'PDF report generated successfully! Opening in a new tab.';
                });
            } else if (contentType && contentType.includes('text/html')) {
                // For HTML: Open the response in a new tab
                return response.text().then(html => {
                    const newTab = window.open();
                    newTab.document.write(html);
                    newTab.document.close();
                    responseMessage.textContent = 'HTML report generated successfully! Opening in a new tab.';
                });
            } else {
                // For other types, just download the file
                const disposition = response.headers.get('content-disposition');
                let filename = 'report';
                if (disposition && disposition.includes('filename=')) {
                    filename = disposition.split('filename=')[1].replace(/"/g, '');
                }
                
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    responseMessage.textContent = 'Report generated successfully! Downloading file.';
                });
            }
        })
        .catch(error => {
            // Display error message
            console.error('Error:', error);
            responseMessage.textContent = 'Error: ' + error.message;
        });
    });
});