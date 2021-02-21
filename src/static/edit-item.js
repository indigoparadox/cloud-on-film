
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
 
       let treeLoaded = $.Deferred();
       let treeLoadFinished = false;
 
       $('#form-edit-tree').jstree( {
            core: {
                data: {
                    url: flaskRoot + 'ajax/folders',
                    data: function( node ) {
                        return {  id: node.id };
                    }
                }
            }
        } );
        $('#form-edit-tree').on( 'loaded.jstree', function( e, treeData ) {
            // Open the root first.
            let rootNode = treeData.instance.element.find( '#root' );
            treeData.instance.open_node( rootNode );
        } );
        $('#form-edit-tree').on( 'after_open.jstree', function( e, parentNode ) {
            if( treeLoadFinished ) {
                return;
            }
 
            // Iterate through current item's parents starting from the root.
            let parentIdx = 0;
            for( parentIdx in itemData['parents'] ) {
                parentID = itemData['parents'][parentIdx];
    
                // Try to find the current parent in the tree's loaded nodes and open it.
                parentNode.instance.element.find( '#' + parentID ).each( function( i ) {
                    parentNode.instance.open_node( $(this) );
                    if( parentIdx == itemData['parents'].length - 1 ) {
                    // Last parent should be visible, now.
                    treeLoaded.resolve( parentNode, this );
                    }
                } );
            }
        } );
 
        $('#edit-modal').modal( 'show' );
    
        $.when( treeLoaded ).done( function( parentNode, node ) {
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