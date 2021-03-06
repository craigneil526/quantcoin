import binascii
import hashlib

from transaction import Transaction


class Block:
    """
    Blocks are the links of a blockchain. Every block register the history of
    transactions made in this network. Miners produce blocks by validating
    every transaction they receive, if the transaction is valid, the miner
    tries to include this transaction in the next block if it is his best
    interest(The commission can influence what transactions are included first
    in the blocks). To a block be accepted by the network, its transactions
    are validated again by other nodes.

    Only one coin creation transaction is allowed by the node validation of
    blocks. The coin creation transaction can have as many target addresses
    as the miner wants, but the total coins created by this special transaction
    is limited by the block validation as well.
    """

    def __init__(self, author, transactions, previous_block, nonce=None,
                 digest=None):
        """
        Instantiates a block. Every block has an author, a set of transactions,
        a reference to a previous block, a nonce and a digest value. But
        this constructor supports the creation of a block without a nonce and
        digest value for the purposes of mining. But for persisting the block
        both these values are mandated.

        :param author: the address of the wallet of the miner
        :param transactions: a set of transactions included in this block
        :param previous_block: a digest that references the previous block
        :param nonce: the nonce value used to achieve the requested zeroes to
                include this block in the chain
        :param digest: the digest value of this block
        """
        if author is None:
            raise Exception("A block must have an author.")
        if transactions is None:
            raise Exception("A block should contain at least one transaction.")
        if previous_block is None:
            raise Exception("A block must contain a reference to a " +
                            "previous one.")

        self._author = author
        self._transactions = transactions
        self._previous_block = previous_block
        self._nonce = nonce
        self._digest = digest

    @staticmethod
    def from_json(data):
        """
        Parses a JSON of a block.

        :returns The block instance represented by the JSON object.
        """
        transactions = []
        if 'transactions' in data.keys():
            for transaction in data['transactions']:
                transaction_object = Transaction(transaction['body']['from_wallet'],
                                                 transaction['body']['to_wallets'],
                                                 transaction['signature'],
                                                 transaction['public_key'])
                transactions.append(transaction_object)

        block = Block(data['author'], transactions,
                      binascii.a2b_base64(data['previous']),
                      data['nonce'],
                      binascii.a2b_base64(data['digest']))
        return block

    def json(self):
        """
        Encode this block in JSON.
        """
        if self.nonce() is not None:
            previous = self.previous() \
                if self.previous() is not None else None
            dictionary = {
                'author': self.author(),
                'nonce': self.nonce(),
                'digest': self.digest(),
                'previous': previous,
                'transactions': [t.json() for t in self.transactions()]
            }

            return dictionary

    def transactions(self):
        """
        :returns the set of transactions included in this block sorted.
        """
        return sorted(self._transactions,
                      lambda transaction1, transaction2:
                      transaction1.from_wallet() < transaction2.from_wallet())

    def previous(self):
        """
        :returns the reference to the previous block.
        """
        return binascii.b2a_base64(self._previous_block)

    def commission(self):
        """
        :return: The sum of all commissions earned in this block
        """
        commission = 0.0
        for transaction in self.transactions():
            commission += transaction.commission()

        return commission

    def transactions_digest(self):
        """
        Obtains the digest value of the tree root of the transactions digests
        """
        ordered_transactions = self.transactions()
        if len(ordered_transactions) == 0:
            return hashlib.sha256("").digest()

        queue = []
        for transaction in ordered_transactions:
            queue.append(hashlib.sha256(transaction.json()).digest())

        if len(queue) % 2 == 1:  # we have and odd number of transactions
            queue.append("")  # append and empty string

        while len(queue) > 1:
            pair, queue = queue[:2], queue[2:]
            pair_hash = hashlib.sha256(pair[0] + pair[1]).digest()
            queue.append(pair_hash)

        return queue[0]

    def proof_of_work(self, difficulty, start_nonce, end_nonce):
        """
        Does the search for a nonce value that results in a digest value that
        satisfies the blockchain requirements to include this block.

        :param difficulty: the difficulty required by the blockchain
        :param start_nonce: the nonce to begin the search
        :param end_nonce: the nonce to end the search
        """
        if self._nonce is None:
            zeros = [0 for _ in range(difficulty)]
            transactions_digest = self.transactions_digest()
            nonce = start_nonce
            digest = hashlib.sha256(self.author() + self.previous() +
                                    transactions_digest + str(nonce)).digest()
            while digest[:difficulty] != bytearray(zeros):
                nonce = nonce + 1
                if nonce > end_nonce:
                    return False

                digest = hashlib.sha256(self.author() + self.previous() +
                                        transactions_digest + str(nonce)).digest()

            self._nonce = nonce
            self._digest = digest
            return True
        else:
            return True

    def valid(self, difficulty):
        """
        Checks if the block is valid.
        """
        if self._nonce is not None:
            zeros = [0 for _ in range(difficulty)]
            transactions_digest = self.transactions_digest()
            calculated_digest = hashlib.sha256(self.author() +
                                               self.previous() +
                                               transactions_digest +
                                               str(self._nonce)).digest()
            return calculated_digest == self._digest and \
                calculated_digest[:difficulty] == bytearray(zeros)
        else:
            return False

    def nonce(self):
        """
        The nonce value of this block.
        """
        return self._nonce

    def digest(self):
        """
        The digest value of this block
        """
        return binascii.b2a_base64(self._digest)

    def author(self):
        """
        Returns the address of the author of this block.
        """
        return self._author.encode('utf-8')

    def __eq__(self, other):
        if not isinstance(other, Block):
            return False

        return self.digest() == other.digest()
