"""Consumer-independent declaration and bounded screen-scope checks."""
import unittest

from tools.experiments import game_texture_vertex_span_fit as fit


class TextureVertexSpanFitCandidateTests(unittest.TestCase):
    def test_declarations_preserve_every_statement_and_real_local(self):
        marker='    func_1510D0EC(resource, &extent, 3, 0);'
        self.assertEqual(fit.SEED.split(marker,1)[1],fit.HOMES.split(marker,1)[1])
        declarations=lambda text:sorted(line.strip() for line in text.split(marker,1)[0].splitlines()[2:] if line.strip())
        self.assertEqual(declarations(fit.SEED),declarations(fit.HOMES))
        with self.assertRaises(AssertionError):
            fit.declare(fit.SEED,['extent'])
        self.assertNotIn('volatile',fit.HOMES)
        self.assertNotIn('register ',fit.HOMES)

    def test_screen_labels_are_bounded_and_distinct(self):
        groups=(fit.variants,fit.home_variants,fit.return_variants,fit.control_variants,fit.exit_variants,fit.advisory_variants)
        counts=[len(list(forms())) for forms in groups]
        self.assertEqual(counts,[36,15,8,8,28,7])
        for forms in groups:
            labels=[label for label,_ in forms()]
            self.assertEqual(len(labels),len(set(labels)))
        self.assertEqual(len(list(fit.advisory_variants())),7)


if __name__=='__main__':
    unittest.main()
