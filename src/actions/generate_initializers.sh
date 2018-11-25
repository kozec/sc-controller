#!/bin/bash
SOURCE_ROOT=$(dirname "$0")/../..

function get_names {
	while [ x"$1" != "x" ] ; do
		grep -h "scc_actions_init_" "$SOURCE_ROOT"/"$1" \
			| sed "s/void//" \
			| tr -d "{(;)}\n"
		echo -n " "
		shift
	done
}

NAMES=$(get_names $@)
for name in $NAMES; do
	echo "void $name();"
done
echo
echo "static inline void scc_run_action_initializers() {"
for name in $NAMES; do
	echo "	$name();"
done
echo "}"
