// https://stackoverflow.com/questions/33732655/html-file-upload-why-use-iframe
function redirect()
{
    //'my_iframe' is the name of the iframe
    document.getElementById('upload_form').target = 'my_iframe';
    document.getElementById('upload_form').submit();
}

