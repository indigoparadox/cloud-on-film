
(function( $ ) {

$().ready( function() {

    // Setup tags autocomplete.
    tagnames = new Bloodhound( {
    datumTokenizer: function( d ) {
        var tokens = d.name.split( /[\s\/]+/ );
        //console.log( tokens );
        return tokens;
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    prefetch: {
        url: flaskRoot + 'ajax/tags.json',
            filter: function( list ) {
                return $.map( list, function( tagname ) {
                    return { name: tagname }; 
                } );
            }
        }
    } );

    tagnames.clearPrefetchCache();
    tagnames.initialize();
} );

}( jQuery ));

function editItem( id ) {

    $.getJSON( flaskRoot + 'ajax/item/' + id.toString() + '/json',
    function( itemData ) {
       console.log( itemData );
       
        $('#form-edit #tags').tagsinput( {
            tagClass: function( name ) {
                return 'bg-dark';
            },
            typeaheadjs: {
                name: 'tagnames',
                displayKey: 'name',
                valueKey: 'name',
                source: tagnames.ttAdapter()
            }
        } );
 
       $('#form-edit #id').val( id );
       $('#form-edit-type').text( itemData['check']['type'] );
       $('#form-edit-type').attr( 'class',
            'ok' == itemData['check']['status'] ? 
            'text-success' : 'text-danger' );
        $('#form-edit #tags').tagsinput( 'removeAll' );
        for( const tag_idx in itemData['tags'] ) {
            $('#form-edit #tags').tagsinput(
                'add', itemData['tags'][tag_idx] );
        }
        $('#form-edit #name').val( itemData['name'] );
        $('#form-edit #comment').val( itemData['comment'] );
        let img_preview_tag = $('<img src="' + flaskRoot + 'preview/' +
            itemData['id'] + '/230/172" id="form-edit-preview-img" ' +
            'class="d-block w-100" style="display: none;" />');
        $('#form-edit-preview').empty();
        $('#form-edit-preview').append( img_preview_tag );
        $('#form-edit-preview-img').one( 'load', function( e ) {
            $(this).fadeIn();
        } );
 
        $('#edit-modal').modal( 'show' );
        
        $.when( $('#form-edit-tree').enableBrowserTree( flaskRoot + 'ajax/folders', itemData['parents'] ) )
        .done( function( parentNode, node ) {
            // All parents are loaded, so select the last one.
            parentNode.instance.deselect_all();
            parentNode.instance.select_node( node, true );
            console.assert( 1 == parentNode.instance.get_selected( true ).length );
            treeLoadFinished = true;
        } );
    } );
 
    return false;
 }
 
 function saveEdit() {
 
    let moveSelected = $('#form-edit-tree').jstree( 'get_selected', true )[0];
    console.log( $('#form-edit-tree').jstree( 'get_selected', true ) );
    // Build the path using IDs, as those are simpler to parse server-side.
    let movePath = $('#form-edit-tree').jstree().get_path( moveSelected, '/', true );
    $('#form-edit #location').val( movePath );
    
    $.ajax( {
        url: flaskRoot + 'ajax/item/save',
        data: $('#form-edit').serialize(),
        type: 'POST',
        success: function( data ) {
            console.log( data );
            $('#edit-modal').modal( 'hide' );
        }
    } );
 
    return false;
 }