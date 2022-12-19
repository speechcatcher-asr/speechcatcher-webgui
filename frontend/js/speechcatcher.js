window.onload = function(){
    updateStatus(true);
    updateDownloads(true);
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

// https://stackoverflow.com/questions/25983603/how-to-submit-an-html-form-without-redirection
function urlFormSubmit(event) {
  var url = "sc/apiv1/process_url";
  var request = new XMLHttpRequest();
  request.open('POST', url, true);
  request.onload = function() { // request successful
  // we can use server response to our request now
    console.log(request.responseText);
    jQuery.noticeAdd({text: 'Added new download job.', stay: false});
  };

  request.onerror = function() {
    // request failed
    jQuery.noticeAdd({text: 'Error in adding new download job.', stay: false});
  };

  request.send(new FormData(event.target)); // create FormData from form that triggered event
  event.preventDefault();
  setInterval(updateStatus, 3000);
}

/*cancels either a queued job or a running job, if kill is set to true*/
function cancelAsrJob(job_id, kill=false) {
  console.log((kill ? "kill job" : "cancel job") + job_id);  
 
  var endpoint = '';
  if (kill) { 
     endpoint = `/sc/apiv1/kill_job/${job_id}`;
  } else {
     endpoint = `/sc/apiv1/cancel_job/${job_id}`;
  }

  fetch(endpoint, {method: 'GET',}).then(data => {
    jQuery.noticeAdd({text: 'Job '+job_id+' cancelled', stay: false});
  }).catch(error => {
    console.error(error);
    jQuery.noticeAdd({text: 'Error in cancelling job: ' + job_id + '. Error:' + error, stay: false});
  });

  setInterval(updateStatus, 3000);

  return false;
}

document.getElementById('upload_url_form').addEventListener("submit", urlFormSubmit);

// https://stackoverflow.com/questions/33732655/html-file-upload-why-use-iframe
function redirect()
{
    document.getElementById('upload_form').target = 'my_iframe';
    document.getElementById('upload_form').submit();
    setInterval(updateStatus, 3000);
}
