var jobsTemplate = doT.template(document.getElementById('jobs-template').text);

function updateStatus()
{
    $.get( "/status", function( data ) {
        console.log(data);
        var jobs_view_data = $(jobsTemplate(data));
        console.log(jobs_view_data);
        $('#job_view').html(jobs_view_data);
    });
}

// https://stackoverflow.com/questions/33732655/html-file-upload-why-use-iframe
function redirect()
{
    //'my_iframe' is the name of the iframe
    document.getElementById('upload_form').target = 'my_iframe';
    document.getElementById('upload_form').submit();
}

