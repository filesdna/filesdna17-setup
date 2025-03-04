function createLoader() {
    const container = document.createElement('div');
    container.setAttribute('id', 'loader');
    container.style.position = 'fixed';
    container.style.top = '0';
    container.style.left = '0';
    container.style.width = '100vw';
    container.style.height = '100vh';
    container.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    container.style.display = 'none';
  
    const spinner = document.createElement('div');
    spinner.classList.add('spinner');
    spinner.style.width = '50px';
    spinner.style.height = '50px';
    spinner.style.borderRadius = '50%';
    spinner.style.borderWidth = '10px';
    spinner.style.borderStyle = 'solid';
    spinner.style.borderColor = '#f3f3f3 transparent #3498db transparent';
    spinner.style.position = 'absolute';
    spinner.style.top = '50%';
    spinner.style.left = '50%';
    spinner.style.transform = 'translate(-50%, -50%)';
    spinner.style.animation = 'spin 2s linear infinite';
  
    container.appendChild(spinner);
  
    const styleElement = document.createElement('style');
    styleElement.innerHTML = `
      @keyframes spin {
        0% {
          transform: rotate(0deg);
        }
        100% {
          transform: rotate(360deg);
        }
      }
    `;
  
    document.head.appendChild(styleElement);
  
    document.body.appendChild(container);
  
    return container;
  }
  
  const loader = createLoader();
  
$(function() {
    $('.restore_database').on('click', function(event) {

        const buttons = document.getElementsByClassName('restore_database');
        for (let i = 0; i < buttons.length; i++) {
            buttons[i].disabled = true;
        }
        

        // Get database path and list ID
        var database_path = $(event.currentTarget).val();
        var database_list_id = $(event.currentTarget).closest('td').find('input').val();

        loader.style.display = 'block';
        $.ajax({
            type: "POST",
            dataType: "json",
            url: "/apps/restore_database",
            contentType: "application/json; charset=utf-8",
            data: JSON.stringify({ 'jsonrpc': "2.0", 'method': "call", 'params': { 'db_id': database_list_id, 'db_path': database_path } }),
            success: function(action) {
                loader.style.display = 'none';
                if (action.result) {
                    alert("Database Restoration Completed Successfully!!");
                    window.location.reload();
                } else {
                    alert("Database restoration failed: " + action.error);
                }


                for (let i = 0; i < buttons.length; i++) {
                    buttons[i].disabled = false;
                }
            }
        });
    });
});
// End