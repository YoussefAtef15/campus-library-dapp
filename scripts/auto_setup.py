import json
import os
import sys
from web3 import Web3

# Configuration variables
GANACHE_URL = "http://127.0.0.1:7545"
CONFIG_FILE = "../config.json"

# =====================================================================
# ABI and Bytecode from Remix
# =====================================================================

# 1. Library Coin
COIN_ABI = [
    {
        "inputs": [],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address"
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "spender",
                "type": "address"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256"
            }
        ],
        "name": "Approval",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "Minted",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "previousAdmin",
                "type": "address"
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "newAdmin",
                "type": "address"
            }
        ],
        "name": "OwnershipTransferred",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "from",
                "type": "address"
            },
            {
                "indexed": True,
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256"
            }
        ],
        "name": "Transfer",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "admin",
        "outputs": [
            {
                "internalType": "address",
                "name": "",
                "type": "address"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "owner",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "spender",
                "type": "address"
            }
        ],
        "name": "allowance",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "spender",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "approve",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "account",
                "type": "address"
            }
        ],
        "name": "balanceOf",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [
            {
                "internalType": "uint8",
                "name": "",
                "type": "uint8"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "name",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [
            {
                "internalType": "string",
                "name": "",
                "type": "string"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "transfer",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "from",
                "type": "address"
            },
            {
                "internalType": "address",
                "name": "to",
                "type": "address"
            },
            {
                "internalType": "uint256",
                "name": "amount",
                "type": "uint256"
            }
        ],
        "name": "transferFrom",
        "outputs": [
            {
                "internalType": "bool",
                "name": "",
                "type": "bool"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "newAdmin",
                "type": "address"
            }
        ],
        "name": "transferOwnership",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Bytecode for LibraryCoin
COIN_BIN = "60806040526040518060400160405280600c81526020017f4c69627261727920436f696e0000000000000000000000000000000000000000815250600090816200004a91906200037d565b506040518060400160405280600381526020017f4c42430000000000000000000000000000000000000000000000000000000000815250600190816200009191906200037d565b506012600260006101000a81548160ff021916908360ff160217905550348015620000bb57600080fd5b5033600460006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555062000464565b600081519050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fd5b600060028204905060018216806200018557607f821691505b6020821081036200019b576200019a6200013d565b5b50919050565b60008190508160005260206000209050919050565b60006020601f8301049050919050565b600082821b905092915050565b600060088302620002057fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff82620001c6565b620002118683620001c6565b95508019841693508086168417925050509392505050565b6000819050919050565b6000819050919050565b60006200025e62000258620002528462000229565b62000233565b62000229565b9050919050565b6000819050919050565b6200027a836200023d565b62000292620002898262000265565b848454620001d3565b825550505050565b600090565b620002a96200029a565b620002b68184846200026f565b505050565b5b81811015620002de57620002d26000826200029f565b600181019050620002bc565b5050565b601f8211156200032d57620002f781620001a1565b6200030284620001b6565b8101602085101562000312578190505b6200032a6200032185620001b6565b830182620002bb565b50505b505050565b600082821c905092915050565b6000620003526000198460080262000332565b1980831691505092915050565b60006200036d83836200033f565b9150826002028217905092915050565b620003888262000103565b67ffffffffffffffff811115620003a457620003a36200010e565b5b620003b082546200016c565b620003bd828285620002e2565b600060209050601f831160018114620003f55760008415620003e0578287015190505b620003ec85826200035f565b8655506200045c565b601f1984166200040586620001a1565b60005b828110156200042f5784890151825560018201915060208501945060208101905062000408565b868310156200044f57848901516200044b601f8916826200033f565b8355505b6001600288020188555050505b505050505050565b611a6380620004746000396000f3fe608060405234801561001057600080fd5b50600436106100b45760003560e01c806370a082311161007157806370a082311461018f57806395d89b41146101bf578063a9059cbb146101dd578063dd62ed3e1461020d578063f2fde38b1461023d578063f851a44014610259576100b4565b806306fdde03146100b9578063095ea7b3146100d757806318160ddd1461010757806323b872dd14610125578063313ce5671461015557806340c10f1914610173575b600080fd5b6100c1610277565b6040516100ce919061112c565b60405180910390f35b6100f160048036038101906100ec91906111e7565b610305565b6040516100fe9190611242565b60405180910390f35b61010f610465565b60405161011c919061126c565b60405180910390f35b61013f600480360381019061013a9190611287565b61046b565b60405161014c9190611242565b60405180910390f35b61015d61083a565b60405161016a91906112f6565b60405180910390f35b61018d600480360381019061018891906111e7565b61084d565b005b6101a960048036038101906101a49190611311565b610ab6565b6040516101b6919061126c565b60405180910390f35b6101c7610aff565b6040516101d4919061112c565b60405180910390f35b6101f760048036038101906101f291906111e7565b610b8d565b6040516102049190611242565b60405180910390f35b6102276004803603810190610222919061133e565b610d9a565b604051610234919061126c565b60405180910390f35b61025760048036038101906102529190611311565b610e21565b005b610261611076565b60405161026e919061138d565b60405180910390f35b60008054610284906113d7565b80601f01602080910402602001604051908101604052809291908181526020018280546102b0906113d7565b80156102fd5780601f106102d2576101008083540402835291602001916102fd565b820191906000526020600020905b8154815290600101906020018083116102e057829003601f168201915b505050505081565b60008073ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff1603610375576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161036c9061147a565b60405180910390fd5b81600660003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055508273ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167f8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b92584604051610453919061126c565b60405180910390a36001905092915050565b60035481565b60008073ffffffffffffffffffffffffffffffffffffffff168473ffffffffffffffffffffffffffffffffffffffff16036104db576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016104d29061150c565b60405180910390fd5b600073ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff160361054a576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016105419061159e565b60405180910390fd5b81600560008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205410156105cc576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016105c390611630565b60405180910390fd5b81600660008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054101561068b576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016106829061169c565b60405180910390fd5b81600560008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008282546106da91906116eb565b9250508190555081600560008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254610730919061171f565b9250508190555081600660008673ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008282546107c391906116eb565b925050819055508273ffffffffffffffffffffffffffffffffffffffff168473ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef84604051610827919061126c565b60405180910390a3600190509392505050565b600260009054906101000a900460ff1681565b600460009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff16146108dd576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016108d4906117c5565b60405180910390fd5b600073ffffffffffffffffffffffffffffffffffffffff168273ffffffffffffffffffffffffffffffffffffffff160361094c576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161094390611857565b60405180910390fd5b6000811161098f576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610986906118e9565b60405180910390fd5b80600360008282546109a1919061171f565b9250508190555080600560008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008282546109f7919061171f565b925050819055508173ffffffffffffffffffffffffffffffffffffffff16600073ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef83604051610a5c919061126c565b60405180910390a38173ffffffffffffffffffffffffffffffffffffffff167f30385c845b448a36257a6a1716e6ad2e1bc2cbe333cde1e69fe849ad6511adfe82604051610aaa919061126c565b60405180910390a25050565b6000600560008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020549050919050565b60018054610b0c906113d7565b80601f0160208091040260200160405190810160405280929190818152602001828054610b38906113d7565b8015610b855780601f10610b5a57610100808354040283529160200191610b85565b820191906000526020600020905b815481529060010190602001808311610b6857829003601f168201915b505050505081565b60008073ffffffffffffffffffffffffffffffffffffffff168373ffffffffffffffffffffffffffffffffffffffff1603610bfd576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610bf49061159e565b60405180910390fd5b81600560003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020541015610c7f576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610c7690611630565b60405180910390fd5b81600560003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254610cce91906116eb565b9250508190555081600560008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254610d24919061171f565b925050819055508273ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef84604051610d88919061126c565b60405180910390a36001905092915050565b6000600660008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054905092915050565b600460009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614610eb1576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610ea8906117c5565b60405180910390fd5b600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1603610f20576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610f179061197b565b60405180910390fd5b600460009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1603610fb0576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610fa790611a0d565b60405180910390fd5b6000600460009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905081600460006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055508173ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff167f8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e060405160405180910390a35050565b600460009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1681565b600081519050919050565b600082825260208201905092915050565b60005b838110156110d65780820151818401526020810190506110bb565b60008484015250505050565b6000601f19601f8301169050919050565b60006110fe8261109c565b61110881856110a7565b93506111188185602086016110b8565b611121816110e2565b840191505092915050565b6000602082019050818103600083015261114681846110f3565b905092915050565b600080fd5b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b600061117e82611153565b9050919050565b61118e81611173565b811461119957600080fd5b50565b6000813590506111ab81611185565b92915050565b6000819050919050565b6111c4816111b1565b81146111cf57600080fd5b50565b6000813590506111e1816111bb565b92915050565b600080604083850312156111fe576111fd61114e565b5b600061120c8582860161119c565b925050602061121d858286016111d2565b9150509250929050565b60008115159050919050565b61123c81611227565b82525050565b60006020820190506112576000830184611233565b92915050565b611266816111b1565b82525050565b6000602082019050611281600083018461125d565b92915050565b6000806000606084860312156112a05761129f61114e565b5b60006112ae8682870161119c565b93505060206112bf8682870161119c565b92505060406112d0868287016111d2565b9150509250925092565b600060ff82169050919050565b6112f0816112da565b82525050565b600060208201905061130b60008301846112e7565b92915050565b6000602082840312156113275761132661114e565b5b60006113358482850161119c565b91505092915050565b600080604083850312156113555761135461114e565b5b60006113638582860161119c565b92505060206113748582860161119c565b9150509250929050565b61138781611173565b82525050565b60006020820190506113a2600083018461137e565b92915050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fd5b600060028204905060018216806113ef57607f821691505b602082108103611402576114016113a8565b5b50919050565b7f4c696272617279436f696e3a20617070726f766520746f20746865207a65726f60008201527f2061646472657373000000000000000000000000000000000000000000000000602082015250565b60006114646028836110a7565b915061146f82611408565b604082019050919050565b6000602082019050818103600083015261149381611457565b9050919050565b7f4c696272617279436f696e3a207472616e736665722066726f6d20746865207a60008201527f65726f2061646472657373000000000000000000000000000000000000000000602082015250565b60006114f6602b836110a7565b91506115018261149a565b604082019050919050565b60006020820190508181036000830152611525816114e9565b9050919050565b7f4c696272617279436f696e3a207472616e7366657220746f20746865207a657260008201527f6f20616464726573730000000000000000000000000000000000000000000000602082015250565b60006115886029836110a7565b91506115938261152c565b604082019050919050565b600060208201905081810360008301526115b78161157b565b9050919050565b7f4c696272617279436f696e3a20696e73756666696369656e742062616c616e6360008201527f6500000000000000000000000000000000000000000000000000000000000000602082015250565b600061161a6021836110a7565b9150611625826115be565b604082019050919050565b600060208201905081810360008301526116498161160d565b9050919050565b7f4c696272617279436f696e3a20616c6c6f77616e636520657863656564656400600082015250565b6000611686601f836110a7565b915061169182611650565b602082019050919050565b600060208201905081810360008301526116b581611679565b9050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b60006116f6826111b1565b9150611701836111b1565b9250828203905081811115611719576117186116bc565b5b92915050565b600061172a826111b1565b9150611735836111b1565b925082820190508082111561174d5761174c6116bc565b5b92915050565b7f4c696272617279436f696e3a2063616c6c6572206973206e6f7420746865206160008201527f646d696e00000000000000000000000000000000000000000000000000000000602082015250565b60006117af6024836110a7565b91506117ba82611753565b604082019050919050565b600060208201905081810360008301526117de816117a2565b9050919050565b7f4c696272617279436f696e3a206d696e7420746f20746865207a65726f20616460008201527f6472657373000000000000000000000000000000000000000000000000000000602082015250565b60006118416025836110a7565b915061184c826117e5565b604082019050919050565b6000602082019050818103600083015261187081611834565b9050919050565b7f4c696272617279436f696e3a206d696e7420616d6f756e74206d75737420626560008201527f2067726561746572207468616e207a65726f0000000000000000000000000000602082015250565b60006118d36032836110a7565b91506118de82611877565b604082019050919050565b60006020820190508181036000830152611902816118c6565b9050919050565b7f4c696272617279436f696e3a206e65772061646d696e20697320746865207a6560008201527f726f206164647265737300000000000000000000000000000000000000000000602082015250565b6000611965602a836110a7565b915061197082611909565b604082019050919050565b6000602082019050818103600083015261199481611958565b9050919050565b7f4c696272617279436f696e3a206e65772061646d696e2069732073616d65206160008201527f732063757272656e742061646d696e0000000000000000000000000000000000602082015250565b60006119f7602f836110a7565b9150611a028261199b565b604082019050919050565b60006020820190508181036000830152611a26816119ea565b905091905056fea2646970667358221220b268eafe79b06937d30d5f8d8107c845ecd1addd8816f7a95dc2454a5347963064736f6c63430008140033"

# 2. Library Registry
REGISTRY_ABI = [
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "_coinAddress",
				"type": "address"
			}
		],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "title",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "author",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "basePrice",
				"type": "uint256"
			}
		],
		"name": "BookAdded",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "borrower",
				"type": "address"
			},
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "expiresAt",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "finalPrice",
				"type": "uint256"
			}
		],
		"name": "BookBorrowed",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "borrower",
				"type": "address"
			},
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "timestamp",
				"type": "uint256"
			}
		],
		"name": "BookReturned",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "bool",
				"name": "exists",
				"type": "bool"
			}
		],
		"name": "BookStatusChanged",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "title",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "author",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "uint256",
				"name": "basePrice",
				"type": "uint256"
			}
		],
		"name": "BookUpdated",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "previousAdmin",
				"type": "address"
			},
			{
				"indexed": True,
				"internalType": "address",
				"name": "newAdmin",
				"type": "address"
			}
		],
		"name": "OwnershipTransferred",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "by",
				"type": "address"
			}
		],
		"name": "Paused",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "by",
				"type": "address"
			}
		],
		"name": "Resumed",
		"type": "event"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "address",
				"name": "user",
				"type": "address"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "name",
				"type": "string"
			}
		],
		"name": "UserRegistered",
		"type": "event"
	},
	{
		"inputs": [],
		"name": "MAX_BORROW_LIMIT",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "title",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "author",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "basePrice",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "imageHash",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "pdfHash",
				"type": "string"
			},
			{
				"internalType": "uint256[]",
				"name": "durations",
				"type": "uint256[]"
			},
			{
				"internalType": "uint256[]",
				"name": "prices",
				"type": "uint256[]"
			}
		],
		"name": "addBook",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "admin",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string[]",
				"name": "titles",
				"type": "string[]"
			},
			{
				"internalType": "string[]",
				"name": "authors",
				"type": "string[]"
			},
			{
				"internalType": "uint256[]",
				"name": "basePrices",
				"type": "uint256[]"
			},
			{
				"internalType": "string[]",
				"name": "imageHashes",
				"type": "string[]"
			},
			{
				"internalType": "string[]",
				"name": "pdfHashes",
				"type": "string[]"
			},
			{
				"internalType": "uint256[][]",
				"name": "durations",
				"type": "uint256[][]"
			},
			{
				"internalType": "uint256[][]",
				"name": "prices",
				"type": "uint256[][]"
			}
		],
		"name": "batchAddBooks",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "bookCount",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "bookDurations",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "books",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "title",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "author",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "basePrice",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "imageHash",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "pdfHash",
				"type": "string"
			},
			{
				"internalType": "bool",
				"name": "available",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "exists",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "duration",
				"type": "uint256"
			}
		],
		"name": "borrowBook",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "coin",
		"outputs": [
			{
				"internalType": "contract ILibraryCoin",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "durationPrices",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getAdmin",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			}
		],
		"name": "getBook",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "id",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "title",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "author",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "basePrice",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "imageHash",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "pdfHash",
				"type": "string"
			},
			{
				"internalType": "bool",
				"name": "available",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "exists",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			}
		],
		"name": "getBookPricing",
		"outputs": [
			{
				"internalType": "uint256[]",
				"name": "",
				"type": "uint256[]"
			},
			{
				"internalType": "uint256[]",
				"name": "",
				"type": "uint256[]"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			}
		],
		"name": "getLoanCount",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "user",
				"type": "address"
			}
		],
		"name": "getUserBorrowedBooks",
		"outputs": [
			{
				"internalType": "uint256[]",
				"name": "",
				"type": "uint256[]"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			},
			{
				"internalType": "address",
				"name": "user",
				"type": "address"
			}
		],
		"name": "hasActiveAccess",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "isRegistered",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "loanHistory",
		"outputs": [
			{
				"internalType": "address",
				"name": "borrower",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "borrowedAt",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "expiresAt",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "returnedAt",
				"type": "uint256"
			},
			{
				"internalType": "bool",
				"name": "returned",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "pause",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "paused",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			}
		],
		"name": "registerUser",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "resume",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			}
		],
		"name": "returnBook",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			}
		],
		"name": "toggleBookExistence",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "newAdmin",
				"type": "address"
			}
		],
		"name": "transferOwnership",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "bookId",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "title",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "author",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "basePrice",
				"type": "uint256"
			},
			{
				"internalType": "string",
				"name": "imageHash",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "pdfHash",
				"type": "string"
			},
			{
				"internalType": "uint256[]",
				"name": "durations",
				"type": "uint256[]"
			},
			{
				"internalType": "uint256[]",
				"name": "prices",
				"type": "uint256[]"
			}
		],
		"name": "updateBook",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "userBorrowedBooks",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "userNames",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]

# Bytecode for LibraryRegistry
REGISTRY_BIN = "60806040523480156200001157600080fd5b50604051620052033803806200520383398181016040528101906200003791906200014b565b336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060008060146101000a81548160ff021916908315150217905550600060028190555080600160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff160217905550506200017d565b600080fd5b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b60006200011382620000e6565b9050919050565b620001258162000106565b81146200013157600080fd5b50565b60008151905062000145816200011a565b92915050565b600060208284031215620001645762000163620000e1565b5b6000620001748482850162000134565b91505092915050565b615076806200018d6000396000f3fe608060405234801561001057600080fd5b50600436106101c45760003560e01c80638242c320116100f9578063de946c5011610097578063ed26d2b211610071578063ed26d2b21461052a578063f2fde38b1461055a578063f499924b14610576578063f851a440146105a6576101c4565b8063de946c5014610492578063e0ff5b8b146104c3578063ecbfb014146104fa576101c4565b8063a4f45827116100d3578063a4f458271461040c578063b905ad7814610428578063c3c5a54714610446578063ca5140c914610476576101c4565b80638242c320146103ca5780638456cb59146103e65780639645a5e1146103f0576101c4565b80636135ff3011610166578063704f1b9411610140578063704f1b94146103305780637649893a1461034c578063791cf7471461037c5780637f2816351461039a576101c4565b80636135ff30146102ab57806368744046146102db5780636e9960c314610312576101c4565b80631e5eb8a1116101a25780631e5eb8a114610221578063375d2eea1461023d57806351f87964146102715780635c975abb1461028d576101c4565b80630276d87b146101c9578063046f7da2146101f957806311df999514610203575b600080fd5b6101e360048036038101906101de919061302f565b6105c4565b6040516101f0919061307e565b60405180910390f35b6102016105f5565b005b61020b610731565b6040516102189190613118565b60405180910390f35b61023b60048036038101906102369190613341565b610757565b005b6102576004803603810190610252919061302f565b610af5565b6040516102689594939291906134db565b60405180910390f35b61028b6004803603810190610286919061302f565b610b75565b005b610295611363565b6040516102a2919061352e565b60405180910390f35b6102c560048036038101906102c09190613575565b611376565b6040516102d29190613660565b60405180910390f35b6102f560048036038101906102f09190613682565b61140d565b60405161030998979695949392919061372e565b60405180910390f35b61031a61168f565b60405161032791906137c8565b60405180910390f35b61034a600480360381019061034591906137e3565b6116b8565b005b6103666004803603810190610361919061302f565b6118cf565b604051610373919061307e565b60405180910390f35b6103846118f4565b604051610391919061307e565b60405180910390f35b6103b460048036038101906103af9190613575565b6118f9565b6040516103c1919061382c565b60405180910390f35b6103e460048036038101906103df9190613a10565b611999565b005b6103ee611bde565b005b61040a60048036038101906104059190613682565b611d1c565b005b61042660048036038101906104219190613b76565b611fae565b005b610430612342565b60405161043d919061307e565b60405180910390f35b610460600480360381019061045b9190613575565b612348565b60405161046d919061352e565b60405180910390f35b610490600480360381019061048b9190613682565b612368565b005b6104ac60048036038101906104a79190613682565b6127a0565b6040516104ba929190613cc0565b60405180910390f35b6104dd60048036038101906104d89190613682565b6128e2565b6040516104f198979695949392919061372e565b60405180910390f35b610514600480360381019061050f9190613cf7565b612b90565b604051610521919061307e565b60405180910390f35b610544600480360381019061053f9190613682565b612bc1565b604051610551919061307e565b60405180910390f35b610574600480360381019061056f9190613575565b612be1565b005b610590600480360381019061058b9190613d37565b612e30565b60405161059d919061352e565b60405180910390f35b6105ae612f83565b6040516105bb91906137c8565b60405180910390f35b600860205281600052604060002081815481106105e057600080fd5b90600052602060002001600091509150505481565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614610683576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161067a90613de9565b60405180910390fd5b600060149054906101000a900460ff166106d2576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016106c990613e55565b60405180910390fd5b60008060146101000a81548160ff0219169083151502179055503373ffffffffffffffffffffffffffffffffffffffff167f5d287a3a02ade76478d8449abebe9dc45b38421247132b68127dd3cd6c05f3cf60405160405180910390a2565b600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1681565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff16146107e5576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016107dc90613de9565b60405180910390fd5b6003600089815260200190815260200160002060060160019054906101000a900460ff16610848576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161083f90613ee7565b60405180910390fd5b600087511161088c576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161088390613f79565b60405180910390fd5b60008651116108d0576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016108c79061400b565b60405180910390fd5b8051825114610914576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161090b9061409d565b60405180910390fd5b86600360008a8152602001908152602001600020600101908161093791906142bf565b5085600360008a8152602001908152602001600020600201908161095b91906142bf565b5084600360008a81526020019081526020016000206003018190555083600360008a8152602001908152602001600020600401908161099a91906142bf565b5082600360008a815260200190815260200160002060050190816109be91906142bf565b506008600089815260200190815260200160002060006109de9190612fa7565b60005b8251811015610aae57600860008a8152602001908152602001600020838281518110610a1057610a0f614391565b5b60200260200101519080600181540180825580915050600190039060005260206000200160009091909190915055818181518110610a5157610a50614391565b5b6020026020010151600960008b81526020019081526020016000206000858481518110610a8157610a80614391565b5b60200260200101518152602001908152602001600020819055508080610aa6906143ef565b9150506109e1565b50877fcc0a1d10c254e1af1aaf12890d8b5550909f58e65ca69172a5705020b2bb29ac888888604051610ae393929190614437565b60405180910390a25050505050505050565b60046020528160005260406000208181548110610b1157600080fd5b9060005260206000209060050201600091509150508060000160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16908060010154908060020154908060030154908060040160009054906101000a900460ff16905085565b600060149054906101000a900460ff1615610bc5576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610bbc906144ee565b60405180910390fd5b600660003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060009054906101000a900460ff16610c51576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610c4890614580565b60405180910390fd5b6003600083815260200190815260200160002060060160019054906101000a900460ff16610cb4576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610cab90613ee7565b60405180910390fd5b6003600083815260200190815260200160002060060160009054906101000a900460ff16610d17576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610d0e90614612565b60405180910390fd5b6003600760003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000208054905010610d9c576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610d939061467e565b60405180910390fd5b60008060005b6008600086815260200190815260200160002080549050811015610e395783600860008781526020019081526020016000208281548110610de657610de5614391565b5b906000526020600020015403610e265760019250600960008681526020019081526020016000206000858152602001908152602001600020549150610e39565b8080610e31906143ef565b915050610da2565b5081610e7a576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610e7190614710565b60405180910390fd5b6000816003600087815260200190815260200160002060030154610e9e9190614730565b905080600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff166370a08231336040518263ffffffff1660e01b8152600401610efc91906137c8565b602060405180830381865afa158015610f19573d6000803e3d6000fd5b505050506040513d601f19601f82011682018060405250810190610f3d9190614779565b1015610f7e576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610f7590614818565b60405180910390fd5b80600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1663dd62ed3e33306040518363ffffffff1660e01b8152600401610fdc929190614838565b602060405180830381865afa158015610ff9573d6000803e3d6000fd5b505050506040513d601f19601f8201168201806040525081019061101d9190614779565b101561105e576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611055906148d3565b60405180910390fd5b600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff166323b872dd3360008054906101000a900473ffffffffffffffffffffffffffffffffffffffff16846040518463ffffffff1660e01b81526004016110dd939291906148f3565b6020604051808303816000875af11580156110fc573d6000803e3d6000fd5b505050506040513d601f19601f820116820180604052508101906111209190614956565b61115f576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611156906149f5565b60405180910390fd5b60006003600087815260200190815260200160002060060160006101000a81548160ff0219169083151502179055506000844261119c9190614730565b9050600460008781526020019081526020016000206040518060a001604052803373ffffffffffffffffffffffffffffffffffffffff1681526020014281526020018381526020016000815260200160001515815250908060018154018082558091505060019003906000526020600020906005020160009091909190915060008201518160000160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060208201518160010155604082015181600201556060820151816003015560808201518160040160006101000a81548160ff0219169083151502179055505050600760003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020869080600181540180825580915050600190039060005260206000200160009091909190915055853373ffffffffffffffffffffffffffffffffffffffff167fc3e2e9e62c95e66d989d064eea73b7e63c32834946fb5e579bbdc4051ef1b93842848660405161135393929190614a15565b60405180910390a3505050505050565b600060149054906101000a900460ff1681565b6060600760008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002080548060200260200160405190810160405280929190818152602001828054801561140157602002820191906000526020600020905b8154815260200190600101908083116113ed575b50505050509050919050565b6003602052806000526040600020600091509050806000015490806001018054611436906140ec565b80601f0160208091040260200160405190810160405280929190818152602001828054611462906140ec565b80156114af5780601f10611484576101008083540402835291602001916114af565b820191906000526020600020905b81548152906001019060200180831161149257829003601f168201915b5050505050908060020180546114c4906140ec565b80601f01602080910402602001604051908101604052809291908181526020018280546114f0906140ec565b801561153d5780601f106115125761010080835404028352916020019161153d565b820191906000526020600020905b81548152906001019060200180831161152057829003601f168201915b505050505090806003015490806004018054611558906140ec565b80601f0160208091040260200160405190810160405280929190818152602001828054611584906140ec565b80156115d15780601f106115a6576101008083540402835291602001916115d1565b820191906000526020600020905b8154815290600101906020018083116115b457829003601f168201915b5050505050908060050180546115e6906140ec565b80601f0160208091040260200160405190810160405280929190818152602001828054611612906140ec565b801561165f5780601f106116345761010080835404028352916020019161165f565b820191906000526020600020905b81548152906001019060200180831161164257829003601f168201915b5050505050908060060160009054906101000a900460ff16908060060160019054906101000a900460ff16905088565b60008060009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905090565b600060149054906101000a900460ff1615611708576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016116ff906144ee565b60405180910390fd5b600660003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060009054906101000a900460ff1615611795576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161178c90614abe565b60405180910390fd5b60008151116117d9576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016117d090614b50565b60405180910390fd5b80600560003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020908161182591906142bf565b506001600660003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060006101000a81548160ff0219169083151502179055503373ffffffffffffffffffffffffffffffffffffffff167f48cac28ad4dc618e15f4c2dd5e97751182f166de97b25618318b2112aa951a2f826040516118c4919061382c565b60405180910390a250565b6009602052816000526040600020602052806000526040600020600091509150505481565b600381565b60056020528060005260406000206000915090508054611918906140ec565b80601f0160208091040260200160405190810160405280929190818152602001828054611944906140ec565b80156119915780601f1061196657610100808354040283529160200191611991565b820191906000526020600020905b81548152906001019060200180831161197457829003601f168201915b505050505081565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614611a27576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611a1e90613de9565b60405180910390fd5b6000875111611a6b576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611a6290614be2565b60405180910390fd5b85518751148015611a7d575084518651145b8015611a8a575083518551145b8015611a97575082518451145b8015611aa4575081518351145b8015611ab1575080518251145b611af0576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611ae790614c74565b60405180910390fd5b60005b8751811015611bd457611bc1888281518110611b1257611b11614391565b5b6020026020010151888381518110611b2d57611b2c614391565b5b6020026020010151888481518110611b4857611b47614391565b5b6020026020010151888581518110611b6357611b62614391565b5b6020026020010151888681518110611b7e57611b7d614391565b5b6020026020010151888781518110611b9957611b98614391565b5b6020026020010151888881518110611bb457611bb3614391565b5b6020026020010151611fae565b8080611bcc906143ef565b915050611af3565b5050505050505050565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614611c6c576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611c6390613de9565b60405180910390fd5b600060149054906101000a900460ff1615611cbc576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611cb390614ce0565b60405180910390fd5b6001600060146101000a81548160ff0219169083151502179055503373ffffffffffffffffffffffffffffffffffffffff167f62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a25860405160405180910390a2565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614611daa576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611da190613de9565b60405180910390fd5b600081118015611dbc57506002548111155b611dfb576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401611df290614d4c565b60405180910390fd5b6003600082815260200190815260200160002060060160019054906101000a900460ff16156003600083815260200190815260200160002060060160016101000a81548160ff0219169083151502179055506003600082815260200190815260200160002060060160019054906101000a900460ff16611ea95760006003600083815260200190815260200160002060060160006101000a81548160ff021916908315150217905550611f50565b60008060046000848152602001908152602001600020905060008180549050118015611f1457508060018280549050611ee29190614d6c565b81548110611ef357611ef2614391565b5b906000526020600020906005020160040160009054906101000a900460ff16155b15611f1e57600191505b81156003600085815260200190815260200160002060060160006101000a81548160ff02191690831515021790555050505b807fa90b962f43ae4c05536c4cd030ab678357baf254c7050c3e0ff6764df672501a6003600084815260200190815260200160002060060160019054906101000a900460ff16604051611fa3919061352e565b60405180910390a250565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff161461203c576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161203390613de9565b60405180910390fd5b6000875111612080576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161207790613f79565b60405180910390fd5b60008651116120c4576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016120bb9061400b565b60405180910390fd5b8051825114612108576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016120ff9061409d565b60405180910390fd5b6002600081548092919061211b906143ef565b919050555060405180610100016040528060025481526020018881526020018781526020018681526020018581526020018481526020016001151581526020016001151581525060036000600254815260200190815260200160002060008201518160000155602082015181600101908161219691906142bf565b5060408201518160020190816121ac91906142bf565b506060820151816003015560808201518160040190816121cc91906142bf565b5060a08201518160050190816121e291906142bf565b5060c08201518160060160006101000a81548160ff02191690831515021790555060e08201518160060160016101000a81548160ff02191690831515021790555090505060005b82518110156122fa5760086000600254815260200190815260200160002083828151811061225a57612259614391565b5b6020026020010151908060018154018082558091505060019003906000526020600020016000909190919091505581818151811061229b5761229a614391565b5b602002602001015160096000600254815260200190815260200160002060008584815181106122cd576122cc614391565b5b602002602001015181526020019081526020016000208190555080806122f2906143ef565b915050612229565b506002547ff0fcaad7067cab5360bc9a949ef7219d84c55a5c85fc70b87feb39e9c6538def88888860405161233193929190614437565b60405180910390a250505050505050565b60025481565b60066020528060005260406000206000915054906101000a900460ff1681565b600060149054906101000a900460ff16156123b8576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016123af906144ee565b60405180910390fd5b6003600082815260200190815260200160002060060160009054906101000a900460ff161561241c576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161241390614e12565b60405180910390fd5b6000600460008381526020019081526020016000209050600080828054905090505b60008111156125ac573373ffffffffffffffffffffffffffffffffffffffff168360018361246c9190614d6c565b8154811061247d5761247c614391565b5b906000526020600020906005020160000160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1614801561250d5750826001826124db9190614d6c565b815481106124ec576124eb614391565b5b906000526020600020906005020160040160009054906101000a900460ff16155b15612599576001836001836125229190614d6c565b8154811061253357612532614391565b5b906000526020600020906005020160040160006101000a81548160ff021916908315150217905550428360018361256a9190614d6c565b8154811061257b5761257a614391565b5b906000526020600020906005020160030181905550600191506125ac565b80806125a490614e32565b91505061243e565b50806125ed576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016125e490614ecd565b60405180910390fd5b6003600084815260200190815260200160002060060160019054906101000a900460ff16156126465760016003600085815260200190815260200160002060060160006101000a81548160ff0219169083151502179055505b6000600760003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020905060005b818054905081101561274a57848282815481106126ac576126ab614391565b5b9060005260206000200154036127375781600183805490506126ce9190614d6c565b815481106126df576126de614391565b5b90600052602060002001548282815481106126fd576126fc614391565b5b90600052602060002001819055508180548061271c5761271b614eed565b5b6001900381819060005260206000200160009055905561274a565b8080612742906143ef565b91505061268c565b50833373ffffffffffffffffffffffffffffffffffffffff167fae9fffd646f7a413f5aaa489b663b913f7532c702de3def2290eb46ebbad360742604051612792919061307e565b60405180910390a350505050565b60608060006008600085815260200190815260200160002080548060200260200160405190810160405280929190818152602001828054801561280257602002820191906000526020600020905b8154815260200190600101908083116127ee575b505050505090506000815167ffffffffffffffff8111156128265761282561314e565b5b6040519080825280602002602001820160405280156128545781602001602082028036833780820191505090505b50905060005b82518110156128d45760096000878152602001908152602001600020600084838151811061288b5761288a614391565b5b60200260200101518152602001908152602001600020548282815181106128b5576128b4614391565b5b60200260200101818152505080806128cc906143ef565b91505061285a565b508181935093505050915091565b600060608060006060806000806000600360008b8152602001908152602001600020905080600001548160010182600201836003015484600401856005018660060160009054906101000a900460ff168760060160019054906101000a900460ff16868054612950906140ec565b80601f016020809104026020016040519081016040528092919081815260200182805461297c906140ec565b80156129c95780601f1061299e576101008083540402835291602001916129c9565b820191906000526020600020905b8154815290600101906020018083116129ac57829003601f168201915b505050505096508580546129dc906140ec565b80601f0160208091040260200160405190810160405280929190818152602001828054612a08906140ec565b8015612a555780601f10612a2a57610100808354040283529160200191612a55565b820191906000526020600020905b815481529060010190602001808311612a3857829003601f168201915b50505050509550838054612a68906140ec565b80601f0160208091040260200160405190810160405280929190818152602001828054612a94906140ec565b8015612ae15780601f10612ab657610100808354040283529160200191612ae1565b820191906000526020600020905b815481529060010190602001808311612ac457829003601f168201915b50505050509350828054612af4906140ec565b80601f0160208091040260200160405190810160405280929190818152602001828054612b20906140ec565b8015612b6d5780601f10612b4257610100808354040283529160200191612b6d565b820191906000526020600020905b815481529060010190602001808311612b5057829003601f168201915b505050505092509850985098509850985098509850985050919395975091939597565b60076020528160005260406000208181548110612bac57600080fd5b90600052602060002001600091509150505481565b600060046000838152602001908152602001600020805490509050919050565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614612c6f576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401612c6690613de9565b60405180910390fd5b600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1603612cde576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401612cd590614f8e565b60405180910390fd5b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1603612d6c576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401612d6390615020565b60405180910390fd5b60008060009054906101000a900473ffffffffffffffffffffffffffffffffffffffff169050816000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055508173ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff167f8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e060405160405180910390a35050565b6000806004600085815260200190815260200160002090506000818054905090505b6000811115612f76578373ffffffffffffffffffffffffffffffffffffffff1682600183612e809190614d6c565b81548110612e9157612e90614391565b5b906000526020600020906005020160000160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16148015612f21575081600182612eef9190614d6c565b81548110612f0057612eff614391565b5b906000526020600020906005020160040160009054906101000a900460ff16155b15612f635781600182612f349190614d6c565b81548110612f4557612f44614391565b5b90600052602060002090600502016002015442111592505050612f7d565b8080612f6e90614e32565b915050612e52565b5060009150505b92915050565b60008054906101000a900473ffffffffffffffffffffffffffffffffffffffff1681565b5080546000825590600052602060002090810190612fc59190612fc8565b50565b5b80821115612fe1576000816000905550600101612fc9565b5090565b6000604051905090565b600080fd5b600080fd5b6000819050919050565b61300c81612ff9565b811461301757600080fd5b50565b60008135905061302981613003565b92915050565b6000806040838503121561304657613045612fef565b5b60006130548582860161301a565b92505060206130658582860161301a565b9150509250929050565b61307881612ff9565b82525050565b6000602082019050613093600083018461306f565b92915050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b6000819050919050565b60006130de6130d96130d484613099565b6130b9565b613099565b9050919050565b60006130f0826130c3565b9050919050565b6000613102826130e5565b9050919050565b613112816130f7565b82525050565b600060208201905061312d6000830184613109565b92915050565b600080fd5b600080fd5b6000601f19601f8301169050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b6131868261313d565b810181811067ffffffffffffffff821117156131a5576131a461314e565b5b80604052505050565b60006131b8612fe5565b90506131c4828261317d565b919050565b600067ffffffffffffffff8211156131e4576131e361314e565b5b6131ed8261313d565b9050602081019050919050565b82818337600083830152505050565b600061321c613217846131c9565b6131ae565b90508281526020810184848401111561323857613237613138565b5b6132438482856131fa565b509392505050565b600082601f8301126132605761325f613133565b5b8135613270848260208601613209565b91505092915050565b600067ffffffffffffffff8211156132945761329361314e565b5b602082029050602081019050919050565b600080fd5b60006132bd6132b884613279565b6131ae565b905080838252602082019050602084028301858111156132e0576132df6132a5565b5b835b8181101561330957806132f5888261301a565b8452602084019350506020810190506132e2565b5050509392505050565b600082601f83011261332857613327613133565b5b81356133388482602086016132aa565b91505092915050565b600080600080600080600080610100898b03121561336257613361612fef565b5b60006133708b828c0161301a565b985050602089013567ffffffffffffffff81111561339157613390612ff4565b5b61339d8b828c0161324b565b975050604089013567ffffffffffffffff8111156133be576133bd612ff4565b5b6133ca8b828c0161324b565b96505060606133db8b828c0161301a565b955050608089013567ffffffffffffffff8111156133fc576133fb612ff4565b5b6134088b828c0161324b565b94505060a089013567ffffffffffffffff81111561342957613428612ff4565b5b6134358b828c0161324b565b93505060c089013567ffffffffffffffff81111561345657613455612ff4565b5b6134628b828c01613313565b92505060e089013567ffffffffffffffff81111561348357613482612ff4565b5b61348f8b828c01613313565b9150509295985092959890939650565b60006134aa82613099565b9050919050565b6134ba8161349f565b82525050565b60008115159050919050565b6134d5816134c0565b82525050565b600060a0820190506134f060008301886134b1565b6134fd602083018761306f565b61350a604083018661306f565b613517606083018561306f565b61352460808301846134cc565b9695505050505050565b600060208201905061354360008301846134cc565b92915050565b6135528161349f565b811461355d57600080fd5b50565b60008135905061356f81613549565b92915050565b60006020828403121561358b5761358a612fef565b5b600061359984828501613560565b91505092915050565b600081519050919050565b600082825260208201905092915050565b6000819050602082019050919050565b6135d781612ff9565b82525050565b60006135e983836135ce565b60208301905092915050565b6000602082019050919050565b600061360d826135a2565b61361781856135ad565b9350613622836135be565b8060005b8381101561365357815161363a88826135dd565b9750613645836135f5565b925050600181019050613626565b5085935050505092915050565b6000602082019050818103600083015261367a8184613602565b905092915050565b60006020828403121561369857613697612fef565b5b60006136a68482850161301a565b91505092915050565b600081519050919050565b600082825260208201905092915050565b60005b838110156136e95780820151818401526020810190506136ce565b60008484015250505050565b6000613700826136af565b61370a81856136ba565b935061371a8185602086016136cb565b6137238161313d565b840191505092915050565b600061010082019050613744600083018b61306f565b8181036020830152613756818a6136f5565b9050818103604083015261376a81896136f5565b9050613779606083018861306f565b818103608083015261378b81876136f5565b905081810360a083015261379f81866136f5565b90506137ae60c08301856134cc565b6137bb60e08301846134cc565b9998505050505050505050565b60006020820190506137dd60008301846134b1565b92915050565b6000602082840312156137f9576137f8612fef565b5b600082013567ffffffffffffffff81111561381757613816612ff4565b5b6138238482850161324b565b91505092915050565b6000602082019050818103600083015261384681846136f5565b905092915050565b600067ffffffffffffffff8211156138695761386861314e565b5b602082029050602081019050919050565b600061388d6138888461384e565b6131ae565b905080838252602082019050602084028301858111156138b0576138af6132a5565b5b835b818110156138f757803567ffffffffffffffff8111156138d5576138d4613133565b5b8086016138e2898261324b565b855260208501945050506020810190506138b2565b5050509392505050565b600082601f83011261391657613915613133565b5b813561392684826020860161387a565b91505092915050565b600067ffffffffffffffff82111561394a5761394961314e565b5b602082029050602081019050919050565b600061396e6139698461392f565b6131ae565b90508083825260208201905060208402830185811115613991576139906132a5565b5b835b818110156139d857803567ffffffffffffffff8111156139b6576139b5613133565b5b8086016139c38982613313565b85526020850194505050602081019050613993565b5050509392505050565b600082601f8301126139f7576139f6613133565b5b8135613a0784826020860161395b565b91505092915050565b600080600080600080600060e0888a031215613a2f57613a2e612fef565b5b600088013567ffffffffffffffff811115613a4d57613a4c612ff4565b5b613a598a828b01613901565b975050602088013567ffffffffffffffff811115613a7a57613a79612ff4565b5b613a868a828b01613901565b965050604088013567ffffffffffffffff811115613aa757613aa6612ff4565b5b613ab38a828b01613313565b955050606088013567ffffffffffffffff811115613ad457613ad3612ff4565b5b613ae08a828b01613901565b945050608088013567ffffffffffffffff811115613b0157613b00612ff4565b5b613b0d8a828b01613901565b93505060a088013567ffffffffffffffff811115613b2e57613b2d612ff4565b5b613b3a8a828b016139e2565b92505060c088013567ffffffffffffffff811115613b5b57613b5a612ff4565b5b613b678a828b016139e2565b91505092959891949750929550565b600080600080600080600060e0888a031215613b9557613b94612fef565b5b600088013567ffffffffffffffff811115613bb357613bb2612ff4565b5b613bbf8a828b0161324b565b975050602088013567ffffffffffffffff811115613be057613bdf612ff4565b5b613bec8a828b0161324b565b9650506040613bfd8a828b0161301a565b955050606088013567ffffffffffffffff811115613c1e57613c1d612ff4565b5b613c2a8a828b0161324b565b945050608088013567ffffffffffffffff811115613c4b57613c4a612ff4565b5b613c578a828b0161324b565b93505060a088013567ffffffffffffffff811115613c7857613c77612ff4565b5b613c848a828b01613313565b92505060c088013567ffffffffffffffff811115613ca557613ca4612ff4565b5b613cb18a828b01613313565b91505092959891949750929550565b60006040820190508181036000830152613cda8185613602565b90508181036020830152613cee8184613602565b90509392505050565b60008060408385031215613d0e57613d0d612fef565b5b6000613d1c85828601613560565b9250506020613d2d8582860161301a565b9150509250929050565b60008060408385031215613d4e57613d4d612fef565b5b6000613d5c8582860161301a565b9250506020613d6d85828601613560565b9150509250929050565b7f4c69627261727952656769737472793a2063616c6c6572206973206e6f74207460008201527f68652061646d696e000000000000000000000000000000000000000000000000602082015250565b6000613dd36028836136ba565b9150613dde82613d77565b604082019050919050565b60006020820190508181036000830152613e0281613dc6565b9050919050565b7f4c69627261727952656769737472793a206e6f74207061757365640000000000600082015250565b6000613e3f601b836136ba565b9150613e4a82613e09565b602082019050919050565b60006020820190508181036000830152613e6e81613e32565b9050919050565b7f4c69627261727952656769737472793a20626f6f6b20646f6573206e6f74206560008201527f7869737400000000000000000000000000000000000000000000000000000000602082015250565b6000613ed16024836136ba565b9150613edc82613e75565b604082019050919050565b60006020820190508181036000830152613f0081613ec4565b9050919050565b7f4c69627261727952656769737472793a207469746c652063616e6e6f7420626560008201527f20656d7074790000000000000000000000000000000000000000000000000000602082015250565b6000613f636026836136ba565b9150613f6e82613f07565b604082019050919050565b60006020820190508181036000830152613f9281613f56565b9050919050565b7f4c69627261727952656769737472793a20617574686f722063616e6e6f74206260008201527f6520656d70747900000000000000000000000000000000000000000000000000602082015250565b6000613ff56027836136ba565b915061400082613f99565b604082019050919050565b6000602082019050818103600083015261402481613fe8565b9050919050565b7f4c69627261727952656769737472793a206475726174696f6e7320616e64207060008201527f7269636573206c656e677468206d69736d617463680000000000000000000000602082015250565b60006140876035836136ba565b91506140928261402b565b604082019050919050565b600060208201905081810360008301526140b68161407a565b9050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fd5b6000600282049050600182168061410457607f821691505b602082108103614117576141166140bd565b5b50919050565b60008190508160005260206000209050919050565b60006020601f8301049050919050565b600082821b905092915050565b60006008830261417f7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff82614142565b6141898683614142565b95508019841693508086168417925050509392505050565b60006141bc6141b76141b284612ff9565b6130b9565b612ff9565b9050919050565b6000819050919050565b6141d6836141a1565b6141ea6141e2826141c3565b84845461414f565b825550505050565b600090565b6141ff6141f2565b61420a8184846141cd565b505050565b5b8181101561422e576142236000826141f7565b600181019050614210565b5050565b601f821115614273576142448161411d565b61424d84614132565b8101602085101561425c578190505b61427061426885614132565b83018261420f565b50505b505050565b600082821c905092915050565b600061429660001984600802614278565b1980831691505092915050565b60006142af8383614285565b9150826002028217905092915050565b6142c8826136af565b67ffffffffffffffff8111156142e1576142e061314e565b5b6142eb82546140ec565b6142f6828285614232565b600060209050601f8311600181146143295760008415614317578287015190505b61432185826142a3565b865550614389565b601f1984166143378661411d565b60005b8281101561435f5784890151825560018201915060208501945060208101905061433a565b8683101561437c5784890151614378601f891682614285565b8355505b6001600288020188555050505b505050505050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052603260045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b60006143fa82612ff9565b91507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff820361442c5761442b6143c0565b5b600182019050919050565b6000606082019050818103600083015261445181866136f5565b9050818103602083015261446581856136f5565b9050614474604083018461306f565b949350505050565b7f4c69627261727952656769737472793a20636f6e74726163742069732070617560008201527f7365640000000000000000000000000000000000000000000000000000000000602082015250565b60006144d86023836136ba565b91506144e38261447c565b604082019050919050565b60006020820190508181036000830152614507816144cb565b9050919050565b7f4c69627261727952656769737472793a2075736572206e6f742072656769737460008201527f6572656400000000000000000000000000000000000000000000000000000000602082015250565b600061456a6024836136ba565b91506145758261450e565b604082019050919050565b600060208201905081810360008301526145998161455d565b9050919050565b7f4c69627261727952656769737472793a20626f6f6b206973206e6f742061766160008201527f696c61626c650000000000000000000000000000000000000000000000000000602082015250565b60006145fc6026836136ba565b9150614607826145a0565b604082019050919050565b6000602082019050818103600083015261462b816145ef565b9050919050565b7f4c69627261727952656769737472793a206c696d697420726561636865640000600082015250565b6000614668601e836136ba565b915061467382614632565b602082019050919050565b600060208201905081810360008301526146978161465b565b9050919050565b7f4c69627261727952656769737472793a20696e76616c6964206475726174696f60008201527f6e2073656c656374656400000000000000000000000000000000000000000000602082015250565b60006146fa602a836136ba565b91506147058261469e565b604082019050919050565b60006020820190508181036000830152614729816146ed565b9050919050565b600061473b82612ff9565b915061474683612ff9565b925082820190508082111561475e5761475d6143c0565b5b92915050565b60008151905061477381613003565b92915050565b60006020828403121561478f5761478e612fef565b5b600061479d84828501614764565b91505092915050565b7f4c69627261727952656769737472793a20696e73756666696369656e74204c4260008201527f432062616c616e63650000000000000000000000000000000000000000000000602082015250565b60006148026029836136ba565b915061480d826147a6565b604082019050919050565b60006020820190508181036000830152614831816147f5565b9050919050565b600060408201905061484d60008301856134b1565b61485a60208301846134b1565b9392505050565b7f4c69627261727952656769737472793a20696e73756666696369656e7420616c60008201527f6c6f77616e636500000000000000000000000000000000000000000000000000602082015250565b60006148bd6027836136ba565b91506148c882614861565b604082019050919050565b600060208201905081810360008301526148ec816148b0565b9050919050565b600060608201905061490860008301866134b1565b61491560208301856134b1565b614922604083018461306f565b949350505050565b614933816134c0565b811461493e57600080fd5b50565b6000815190506149508161492a565b92915050565b60006020828403121561496c5761496b612fef565b5b600061497a84828501614941565b91505092915050565b7f4c69627261727952656769737472793a207061796d656e74207472616e73666560008201527f72206661696c6564000000000000000000000000000000000000000000000000602082015250565b60006149df6028836136ba565b91506149ea82614983565b604082019050919050565b60006020820190508181036000830152614a0e816149d2565b9050919050565b6000606082019050614a2a600083018661306f565b614a37602083018561306f565b614a44604083018461306f565b949350505050565b7f4c69627261727952656769737472793a207573657220616c726561647920726560008201527f6769737465726564000000000000000000000000000000000000000000000000602082015250565b6000614aa86028836136ba565b9150614ab382614a4c565b604082019050919050565b60006020820190508181036000830152614ad781614a9b565b9050919050565b7f4c69627261727952656769737472793a206e616d652063616e6e6f742062652060008201527f656d707479000000000000000000000000000000000000000000000000000000602082015250565b6000614b3a6025836136ba565b9150614b4582614ade565b604082019050919050565b60006020820190508181036000830152614b6981614b2d565b9050919050565b7f4c69627261727952656769737472793a207469746c657320617272617920697360008201527f20656d7074790000000000000000000000000000000000000000000000000000602082015250565b6000614bcc6026836136ba565b9150614bd782614b70565b604082019050919050565b60006020820190508181036000830152614bfb81614bbf565b9050919050565b7f4c69627261727952656769737472793a20617272617973206c656e677468206d60008201527f69736d6174636800000000000000000000000000000000000000000000000000602082015250565b6000614c5e6027836136ba565b9150614c6982614c02565b604082019050919050565b60006020820190508181036000830152614c8d81614c51565b9050919050565b7f4c69627261727952656769737472793a20616c72656164792070617573656400600082015250565b6000614cca601f836136ba565b9150614cd582614c94565b602082019050919050565b60006020820190508181036000830152614cf981614cbd565b9050919050565b7f4c69627261727952656769737472793a20696e76616c696420626f6f6b206964600082015250565b6000614d366020836136ba565b9150614d4182614d00565b602082019050919050565b60006020820190508181036000830152614d6581614d29565b9050919050565b6000614d7782612ff9565b9150614d8283612ff9565b9250828203905081811115614d9a57614d996143c0565b5b92915050565b7f4c69627261727952656769737472793a20626f6f6b20697320616c726561647960008201527f20617661696c61626c6500000000000000000000000000000000000000000000602082015250565b6000614dfc602a836136ba565b9150614e0782614da0565b604082019050919050565b60006020820190508181036000830152614e2b81614def565b9050919050565b6000614e3d82612ff9565b915060008203614e5057614e4f6143c0565b5b600182039050919050565b7f4c69627261727952656769737472793a206e6f20616374697665206c6f616e2060008201527f666f756e6420666f722074686973207573657220616e6420626f6f6b00000000602082015250565b6000614eb7603c836136ba565b9150614ec282614e5b565b604082019050919050565b60006020820190508181036000830152614ee681614eaa565b9050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052603160045260246000fd5b7f4c69627261727952656769737472793a206e65772061646d696e20697320746860008201527f65207a65726f2061646472657373000000000000000000000000000000000000602082015250565b6000614f78602e836136ba565b9150614f8382614f1c565b604082019050919050565b60006020820190508181036000830152614fa781614f6b565b9050919050565b7f4c69627261727952656769737472793a206e65772061646d696e20697320736160008201527f6d652061732063757272656e742061646d696e00000000000000000000000000602082015250565b600061500a6033836136ba565b915061501582614fae565b604082019050919050565b6000602082019050818103600083015261503981614ffd565b905091905056fea2646970667358221220a37f4beb73ee9ec78021b97771344d0331db1383a67675d573ea0577bb8beaaa64736f6c63430008140033"


# =====================================================================

def connect_to_ganache():
    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not w3.is_connected():
        print("ERROR: Cannot connect to Ganache. Please ensure Ganache is running.")
        sys.exit(1)
    print("Connected to Ganache. Chain ID:", w3.eth.chain_id)
    return w3


def get_compiled_contracts():
    if not COIN_ABI or not COIN_BIN or not REGISTRY_ABI or not REGISTRY_BIN:
        print("ERROR: Please paste the ABI and Bytecode from Remix into the script first.")
        sys.exit(1)


    return {
        "abi": COIN_ABI,
        "bin": COIN_BIN if COIN_BIN.startswith("0x") else "0x" + COIN_BIN
    }, {
        "abi": REGISTRY_ABI,
        "bin": REGISTRY_BIN if REGISTRY_BIN.startswith("0x") else "0x" + REGISTRY_BIN
    }


def deploy_contract(w3, abi, bytecode, deployer, *constructor_args):
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Build the transaction first to estimate gas
    tx = contract.constructor(*constructor_args).build_transaction({
        "from": deployer,
        "nonce": w3.eth.get_transaction_count(deployer),
        "gasPrice": w3.eth.gas_price
    })

    # Estimate gas dynamically
    estimated_gas = w3.eth.estimate_gas(tx)

    # Send the transaction using the estimated gas
    tx_hash = contract.constructor(*constructor_args).transact({
        "from": deployer,
        "gas": estimated_gas,
        "gasPrice": w3.eth.gas_price
    })

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("  Deployed at:", receipt.contractAddress)
    return receipt.contractAddress


def seed_books(w3, registry_contract, admin):
    titles = [
        "Introduction to Algorithms",
        "Clean Code",
        "The Pragmatic Programmer",
        "Design Patterns",
        "Structure and Interpretation of Computer Programs"
    ]
    authors = [
        "Cormen, Leiserson, Rivest",
        "Robert C. Martin",
        "Andrew Hunt, David Thomas",
        "Gang of Four",
        "Abelson, Sussman"
    ]


    basePrices = [w3.to_wei(2, "ether")] * 5
    imageHashes = [f"Qm_image_hash_{i}" for i in range(5)]
    pdfHashes = [f"Qm_pdf_hash_{i}" for i in range(5)]

    DAY = 86400
    WEEK = 604800
    MONTH = 2592000


    durations = [[DAY, WEEK, MONTH] for _ in range(5)]
    prices = [[w3.to_wei(1, "ether"), w3.to_wei(5, "ether"), w3.to_wei(15, "ether")] for _ in range(5)]
    # -------------------------------------------------------------------------

    print("Seeding books via batchAddBooks ...")
    tx_hash = registry_contract.functions.batchAddBooks(
        titles, authors, basePrices, imageHashes, pdfHashes, durations, prices
    ).transact({
        "from": admin,
        "gas": 3000000
    })
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print("  Seeded", len(titles), "books.")


def mint_initial_coins(w3, coin_contract, admin):
    amount = w3.to_wei(1000, "ether")
    print("Minting 1000 LBC to admin ...")
    tx_hash = coin_contract.functions.mint(admin, amount).transact({
        "from": admin,
        "gas": 1000000
    })
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print("  Minted successfully.")


def save_config(coin_address, coin_abi, registry_address, registry_abi):
    config = {
        "coin": {
            "address": coin_address,
            "abi": coin_abi
        },
        "registry": {
            "address": registry_address,
            "abi": registry_abi
        }
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print("Config saved to", CONFIG_FILE)


def main():
    print("=== Campus Library DApp - Auto Setup (Offline Mode) ===\n")

    w3 = connect_to_ganache()
    admin = w3.eth.accounts[0]
    print("Admin account:", admin, "\n")

    coin_data, registry_data = get_compiled_contracts()

    print("\nDeploying LibraryCoin ...")
    coin_address = deploy_contract(w3, coin_data["abi"], coin_data["bin"], admin)

    print("Deploying LibraryRegistry ...")
    registry_address = deploy_contract(w3, registry_data["abi"], registry_data["bin"], admin, coin_address)

    coin_contract = w3.eth.contract(address=coin_address, abi=coin_data["abi"])
    registry_contract = w3.eth.contract(address=registry_address, abi=registry_data["abi"])

    print()
    seed_books(w3, registry_contract, admin)
    mint_initial_coins(w3, coin_contract, admin)

    save_config(coin_address, coin_data["abi"], registry_address, registry_data["abi"])

    print("\n=== Setup Complete ===")
    print("Registry:", registry_address)
    print("Coin:    ", coin_address)


if __name__ == "__main__":
    main()