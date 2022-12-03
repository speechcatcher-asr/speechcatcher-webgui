window.onload = function(){
    updateStatus(true);
};

var jobsTemplate = doT.template(document.getElementById('jobs-template').text);
var downloadsTemplate = doT.template(document.getElementById('downloads-template').text);

function updateStatus(recursive = false)
{
    $.get( "/sc/apiv1/status", function( data ) {
        console.log(data);
        var jobs_view_html = $(jobsTemplate(data));
        $('#job_view').empty();
        $('#job_view').append(jobs_view_html);
    });

    if (recursive) {
        setInterval(updateStatus, 20000);
    }
}

function updateDownloads(recursive = false)
{
    $.get( "/sc/apiv1/list_outputs", function( data ) {
        console.log(downloadsTemplate(data));
        var download_html = $(downloadsTemplate(data));
        $('#download_view').empty();
        $('#download_view').append(download_html); 
    });

    if (recursive) {
        setInterval(updateDownloads, 20000);
    }
}

// https://stackoverflow.com/questions/33732655/html-file-upload-why-use-iframe
function redirect()
{
    document.getElementById('upload_form').target = 'my_iframe';
    document.getElementById('upload_form').submit();
    setInterval(updateStatus, 3000);
}
