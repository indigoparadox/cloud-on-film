
(function( $ ) {

    $.fn.enableBrowserTree = function( nodesURL, parents=[] ) {
    
        let treeLoaded = $.Deferred();
        let treeLoadFinished = false;

        $(this).jstree( {
            core: {
                data: {
                    url: nodesURL,
                    data: function( node ) {
                        return {  id: node.id };
                    }
                }
            }
        } );
        $(this).on( 'loaded.jstree', function( e, treeData ) {
            // Open the root first.
            let rootNode = treeData.instance.element.find( '#root' );
            treeData.instance.open_node( rootNode );
        } );
        $(this).on( 'after_open.jstree', function( e, parentNode ) {
            if( treeLoadFinished ) {
                console.log( 'finished' );
                return;
            }
 
            // Iterate through current item's parents starting from the root.
            let parentIdx = 0;
            for( parentIdx in parents ) {
                parentID = parents[parentIdx];
    
                // Try to find the current parent in the tree's loaded nodes and open it.
                parentNode.instance.element.find( '#' + parentID ).each( function( i ) {
                    parentNode.instance.open_node( $(this) );
                    if( parentIdx == parents.length - 1 ) {
                    // Last parent should be visible, now.
                    treeLoaded.resolve( parentNode, this );
                    }
                } );
            }
        } );

        return treeLoaded;
    }
 
}( jQuery ));
