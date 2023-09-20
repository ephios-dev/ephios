const {createApp, ref, onUpdated, computed, watch, nextTick} = Vue

document.addEventListener('DOMContentLoaded', (event) => {
    const blocksInput = document.getElementById("id_blocks");
    const blocksInputValue = blocksInput.value;
    blocksInput.value = "";
    const qualifications = JSON.parse(document.getElementById("qualifications_json").value);

    createApp({
        setup() {
            const currentBlock = ref(null);
            const blocks = ref(blocksInputValue ? JSON.parse(blocksInputValue) : []);
            blocks.value.forEach(block => {
                block.deleted = false;
                block.uuid = `${block.id}`;
                block.positions.forEach(position => {
                    position.uuid = `${position.id}`;
                });
            });

            async function addAtomicBlock() {
                const newBlock = {
                    block_type: 'atomic',
                    name: "",
                    allowMore: false,
                    positions: [],
                    qualification_requirements: [],
                    id: null,
                    uuid: `new-${Math.random().toString(36).substring(7)}`,
                }
                blocks.value.push(newBlock);
                currentBlock.value = newBlock;
                // addPosition();
                await nextTick()
                document.getElementById("block-name").focus();
            }

            function addPosition(e) {
                currentBlock.value.positions.push({
                        optional: false,
                        label: "",
                        qualifications: [],
                        id: null,
                        uuid: `new-${Math.random().toString(36).substring(7)}`,
                    }
                );
            }

            function removePosition(position) {
                currentBlock.value.positions = currentBlock.value.positions.filter(p => p.uuid !== position.uuid);
            }

            function removeQualification(position, qualification) {
                position.qualifications = position.qualifications.filter(q => q.pk !== qualification.pk);
            }

            function selectBlock(block) {
                currentBlock.value = block;
            }

            function removeBlock(block) {
                block.deleted = true;
                if (block.uuid.startsWith("new-")) {
                    blocks.value = blocks.value.filter(b => b.uuid !== block.uuid);
                }
                if (currentBlock.value === block) {
                    currentBlock.value = null;
                }
            }

            onUpdated(() => {
                handleForms($('#editor'));
            });

            function participantCountInfo(block) {
                let min = 0;
                let max = 0;
                block.positions.forEach(position => {
                    if (!position.optional) {
                        min += 1;
                    }
                    max += 1;
                });
                if (block.allowMore) {
                    return gettext("{min} or more").replace("{min}", min);
                }
                if (min === max) {
                    return min;
                }
                return gettext("{min} to {max}").replace("{min}", min).replace("{max}", max);
            }

            const undeletedBlocks = computed(() => blocks.value.filter(b => !b.deleted));

            function addQualification(event, position) {
                if (!event.target.value) {
                    return;
                }
                // add new qualification to list
                const newQualification = {
                    id: event.target.value,
                    title: event.target.options[event.target.selectedIndex].text,
                    abbreviation: qualifications[event.target.value].abbreviation,
                };
                event.target.value = "";
                // return if the pk already exists in the list
                if (!position.qualifications.some(q => q.id === newQualification.id)) {
                    position.qualifications.push(newQualification);
                }
            }

            return {
                blocks,
                currentBlock,
                undeletedBlocks,

                addAtomicBlock,
                selectBlock,
                removeBlock,

                addPosition,
                removePosition,
                addQualification,
                removeQualification,
                participantCountInfo,
            }
        },
        delimiters: ['[[', ']]']
    }).mount('#editor');
});