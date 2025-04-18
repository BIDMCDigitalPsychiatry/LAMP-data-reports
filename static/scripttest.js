document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('textForm');
    const responseMessage = document.getElementById('responseMessage');
    let lastHtmlResponse = null;
    let lastTaskId = null;
    
    // Create progress container
    const progressContainer = document.createElement('div');
    progressContainer.id = 'progress-container';
    progressContainer.style.width = '100%';
    progressContainer.style.backgroundColor = '#f0f0f0';
    progressContainer.style.borderRadius = '13px';
    progressContainer.style.padding = '3px';
    progressContainer.style.display = 'none';
    progressContainer.style.marginTop = '10px';

    const progressBar = document.createElement('div');
    progressBar.id = 'progress-bar';
    progressBar.style.width = '0%';
    progressBar.style.height = '20px';
    progressBar.style.backgroundColor = '#4CAF50';
    progressBar.style.borderRadius = '10px';
    progressBar.style.transition = 'width 0.5s ease-in-out';

    progressContainer.appendChild(progressBar);
    responseMessage.parentNode.insertBefore(progressContainer, responseMessage.nextSibling);

    // Create the retry button
    const retryButton = document.createElement('button');
    retryButton.style.display = 'none';
    retryButton.style.marginTop = '10px';
    retryButton.style.padding = '8px 16px';
    retryButton.style.width = '250px';
    retryButton.style.fontSize = '16px';
    retryButton.style.cursor = 'pointer';
    retryButton.style.border = 'none';
    retryButton.style.background = '#FF0000';
    retryButton.style.color = 'white';
    retryButton.style.borderRadius = '5px';
    retryButton.style.textAlign = 'center';
    retryButton.style.position = 'relative';
    retryButton.style.left = '50%';
    retryButton.style.transform = 'translateX(-50%)';
    retryButton.textContent = 'Retry';
    retryButton.onclick = function () {
        if (lastTaskId) {
            const retryWindow = window.open(`/download/${lastTaskId}`, '_blank');
            if (!retryWindow) {
                responseMessage.textContent = 'Pop-up blocked again. Please allow pop-ups to view the report.';
            }
        } else {
            responseMessage.textContent = 'No previous task to retry.';
        }
    };
    
    
    responseMessage.parentNode.insertBefore(retryButton, responseMessage.nextSibling);

    function pollProgress(taskId) {
        const interval = setInterval(() => {
            fetch(`/progress/${taskId}`)
                .then(response => response.json())
                .then(data => {
                    console.log("Progress data:", data);
                    const progress = data.progress;
                    const message = data.message || "";

                    progressBar.style.width = `${progress}%`;
                    responseMessage.textContent = message;

                    if (progress >= 100) {
                        clearInterval(interval);
                        responseMessage.textContent = "Done! Opening report...";
                        progressContainer.style.display = 'none';
                    
                        const reportWindow = window.open(`/download/${taskId}`, '_blank');
                        if (!reportWindow) {
                            responseMessage.textContent = "Pop-up blocked. Please allow pop-ups and click Retry.";
                            retryButton.style.display = 'inline-block';
                        }
                    } else if (progress < 0) {
                        clearInterval(interval);
                        responseMessage.textContent = "Something went wrong. Check the logs.";
                        progressContainer.style.display = 'none';
                    }
                    
                })
                .catch(error => {
                    clearInterval(interval);
                    console.error('Polling error:', error);
                    responseMessage.textContent = "Error checking progress.";
                });
        }, 3000);
    }

    form.addEventListener('submit', function (event) {
        event.preventDefault();

        progressBar.style.width = '0%';
        progressContainer.style.display = 'block';
        responseMessage.textContent = 'Generating report... Please wait.';
        retryButton.style.display = 'none'; 

        const formData = new FormData(form);

        fetch('/generate', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log("Raw /generate response:", response);
            return response.json().catch(err => {
                console.error("JSON parse error from /generate:", err);
                responseMessage.textContent = "Invalid JSON response from server.";
                throw err;
            });
        })
        .then(data => {
            console.log("Parsed /generate JSON:", data);
            lastTaskId = data.task_id;
            if (data.task_id) {
                const taskId = data.task_id;
                console.log("Polling progress for task ID:", taskId);
                pollProgress(taskId);
            } else if (data.error) {
                console.error("Server returned error:", data.error);
                responseMessage.textContent = "Error: " + data.error;
                progressContainer.style.display = 'none';
            } else {
                console.warn("Unexpected /generate response format:", data);
                responseMessage.textContent = "Unexpected response from server.";
                progressContainer.style.display = 'none';
            }
        })
        .catch(error => {
            console.error("Final fetch error:", error);
            responseMessage.textContent = "Error: " + error.message;
            progressContainer.style.display = 'none';
        });        
    });
});
