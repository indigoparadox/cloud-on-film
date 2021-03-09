
//var thread_id = '{{ id }}';
var last_progress = 0;

function updateProgress( url ) {
    $.get( url,
    function( data ) {
        //$('#current-filename').html( data['filename'] );
        if( data['progress'] != last_progress ) {
            $('#thread-progress')
                .css( { 'width': data['progress'] + '%' } );
        }
        last_progress = data['progress'];
        setTimeout( updateProgress, 1000 );
    } );
}
